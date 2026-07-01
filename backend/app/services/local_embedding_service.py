"""
LocalEmbeddingService — fully local semantic embedding generation.

Replaces any external, paid embedding API (OpenAI, Anthropic, ...) with a
sentence-transformers model running in-process. No network calls happen
here: the model is downloaded once (cached on disk by sentence-transformers/
huggingface_hub) and every subsequent embedding call runs locally.

Responsibilities:
  - Load the configured model once (thread-safe singleton) and expose an
    explicit preload() hook for application startup.
  - Build embedding-ready text from a ParsedResume / JobDescription's
    structured_json, normalize it, encode it, L2-normalize the resulting
    vector, and persist it via the repository layer (pgvector columns).
  - Batch-encode multiple resumes in a single model call.
  - Fail gracefully: a model load failure is logged clearly and surfaced as
    embedding_status=FAILED on the affected row rather than crashing silently.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import threading
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.models.embedding import EmbeddingStatus

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

    from app.models.job_description import JobDescription
    from app.models.parsed_resume import ParsedResume
    from app.repositories.job_description import JobDescriptionRepository
    from app.repositories.parsed_resume import ParsedResumeRepository

logger = logging.getLogger(__name__)


class ModelLoadError(Exception):
    """Raised when the local embedding model cannot be loaded."""


# ── Model loading (thread-safe singleton, lazy by default) ─────────────────

_model: SentenceTransformer | None = None
_model_name: str | None = None
_model_lock = threading.Lock()


def _load_model(model_name: str, device: str) -> SentenceTransformer:
    logger.info("Loading local embedding model", extra={"model": model_name, "device": device})
    started = time.monotonic()
    try:
        from sentence_transformers import SentenceTransformer  # lazy import

        model = SentenceTransformer(model_name, device=device)
    except Exception as exc:
        logger.error(
            "Failed to load local embedding model",
            extra={"model": model_name, "device": device, "error": str(exc)},
        )
        raise ModelLoadError(f"Could not load embedding model '{model_name}': {exc}") from exc

    elapsed = time.monotonic() - started
    logger.info(
        "Local embedding model loaded",
        extra={"model": model_name, "device": device, "seconds": round(elapsed, 2)},
    )
    return model


def get_model(
    model_name: str | None = None, device: str | None = None
) -> SentenceTransformer:
    """Return the process-wide model singleton, loading it on first call."""
    global _model, _model_name
    resolved_name = model_name or settings.LOCAL_EMBEDDING_MODEL
    resolved_device = device or settings.LOCAL_EMBEDDING_DEVICE

    if _model is not None and _model_name == resolved_name:
        return _model

    with _model_lock:
        if _model is None or _model_name != resolved_name:
            _model = _load_model(resolved_name, resolved_device)
            _model_name = resolved_name
    return _model


async def preload_model() -> None:
    """
    Load the model once, ahead of the first real request. Intended to be
    called from the application's startup hook.

    Graceful by design: a failure here (no network on first run, no disk
    space, unsupported device, ...) is logged and swallowed rather than
    crashing application startup — the model is still loaded lazily on
    first actual use, so the app remains usable and simply pays the load
    latency on that first call instead.
    """
    try:
        await asyncio.to_thread(get_model)
    except ModelLoadError as exc:
        logger.error("Embedding model preload failed — will retry lazily on first use: %s", exc)


def reset_model_cache() -> None:
    """Test hook: force the next get_model() call to reload."""
    global _model, _model_name
    with _model_lock:
        _model = None
        _model_name = None


# ── Text normalization & vector normalization ───────────────────────────────


def normalize_text(text: str, *, max_chars: int) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    return collapsed[:max_chars]


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


# ── Embedding-ready text builders ───────────────────────────────────────────


def build_resume_embedding_text(structured_json: dict[str, Any]) -> str:
    structured_resume = structured_json.get("structured_resume") or {}
    parts: list[str] = []

    if structured_resume.get("summary"):
        parts.append(structured_resume["summary"])
    if structured_resume.get("skills"):
        parts.append("Skills: " + ", ".join(structured_resume["skills"]))

    for exp in structured_resume.get("experience") or []:
        segment = " ".join(
            filter(None, [exp.get("role"), "at", exp.get("company"), "-", exp.get("description")])
        )
        if segment.strip():
            parts.append(segment)

    for edu in structured_resume.get("education") or []:
        segment = " ".join(
            filter(None, [edu.get("degree"), edu.get("field"), "at", edu.get("institution")])
        )
        if segment.strip():
            parts.append(segment)

    for proj in structured_resume.get("projects") or []:
        segment = " ".join(filter(None, [proj.get("name"), proj.get("description")]))
        if segment.strip():
            parts.append(segment)

    for cert in structured_resume.get("certifications") or []:
        segment = " ".join(filter(None, [cert.get("name"), cert.get("issuer")]))
        if segment.strip():
            parts.append(segment)

    return "\n".join(parts)


def build_job_description_embedding_text(structured_json: dict[str, Any]) -> str:
    job = structured_json.get("job") or {}
    structured_jd = structured_json.get("structured_jd") or {}
    parts: list[str] = []

    header = " ".join(filter(None, [job.get("title"), job.get("employment_type")]))
    if header:
        parts.append(header)
    if job.get("industry"):
        parts.append(f"Industry: {job['industry']}")
    if job.get("location"):
        parts.append(f"Location: {job['location']}")

    exp_min, exp_max = job.get("experience_min") or 0, job.get("experience_max") or 0
    if exp_min or exp_max:
        parts.append(f"Experience: {exp_min}-{exp_max} years")

    if structured_jd.get("required_skills"):
        parts.append("Required skills: " + ", ".join(structured_jd["required_skills"]))
    if structured_jd.get("preferred_skills"):
        parts.append("Preferred skills: " + ", ".join(structured_jd["preferred_skills"]))
    if structured_jd.get("responsibilities"):
        parts.append("Responsibilities: " + "; ".join(structured_jd["responsibilities"]))
    if structured_jd.get("education"):
        parts.append("Education: " + ", ".join(structured_jd["education"]))
    if structured_jd.get("certifications"):
        parts.append("Certifications: " + ", ".join(structured_jd["certifications"]))
    if structured_jd.get("projects"):
        parts.append("Projects: " + ", ".join(structured_jd["projects"]))

    return "\n".join(parts)


# ── LocalEmbeddingService ────────────────────────────────────────────────────


class LocalEmbeddingService:
    """
    Generates and persists embeddings for ParsedResume / JobDescription rows
    using a local sentence-transformers model. Never makes an external API
    call — the only dependency is the locally-loaded model.
    """

    def __init__(
        self,
        parsed_resume_repo: ParsedResumeRepository,
        job_description_repo: JobDescriptionRepository,
        *,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
        max_input_chars: int | None = None,
    ) -> None:
        self.parsed_resume_repo = parsed_resume_repo
        self.job_description_repo = job_description_repo
        self.model_name = model_name or settings.LOCAL_EMBEDDING_MODEL
        self.device = device or settings.LOCAL_EMBEDDING_DEVICE
        self.batch_size = batch_size or settings.LOCAL_EMBEDDING_BATCH_SIZE
        self.max_input_chars = max_input_chars or settings.LOCAL_EMBEDDING_MAX_INPUT_CHARS

    # ── Encoding ──────────────────────────────────────────────────────────

    def _encode_sync(self, texts: list[str]) -> list[list[float]]:
        model = get_model(self.model_name, self.device)
        raw = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [l2_normalize(list(vector)) for vector in raw]

    async def _encode(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode_sync, texts)

    # ── Resume embedding ──────────────────────────────────────────────────

    async def embed_resume(self, parsed_resume_id: uuid.UUID) -> ParsedResume:
        """Embed a single ParsedResume and persist the result."""
        return (await self.embed_resumes([parsed_resume_id]))[0]

    async def embed_resumes(self, parsed_resume_ids: list[uuid.UUID]) -> list[ParsedResume]:
        """
        Batch-embed multiple resumes in a single model call — the point of
        batching is throughput, so this is the primary code path; embed_resume
        is a thin single-item wrapper around it.
        """
        if not parsed_resume_ids:
            return []

        resumes = []
        for rid in parsed_resume_ids:
            resume = await self.parsed_resume_repo.get_by_id(rid)
            if resume is None:
                raise ValueError(f"ParsedResume {rid} not found.")
            if not resume.structured_json:
                raise ValueError(f"ParsedResume {rid} has no structured_json to embed.")
            resumes.append(resume)

        texts = [
            normalize_text(
                build_resume_embedding_text(r.structured_json), max_chars=self.max_input_chars
            )
            for r in resumes
        ]

        for r in resumes:
            await self.parsed_resume_repo.update(r, embedding_status=EmbeddingStatus.GENERATING)

        try:
            vectors = await self._encode(texts)
        except ModelLoadError:
            for r in resumes:
                await self.parsed_resume_repo.update(r, embedding_status=EmbeddingStatus.FAILED)
            raise

        now = datetime.now(timezone.utc)
        updated = []
        for resume, vector in zip(resumes, vectors):
            updated.append(
                await self.parsed_resume_repo.update(
                    resume,
                    embedding=vector,
                    embedding_model=self.model_name,
                    embedding_dimension=len(vector),
                    embedding_generated_at=now,
                    embedding_status=EmbeddingStatus.READY,
                )
            )
        logger.info(
            "Generated resume embeddings",
            extra={"count": len(updated), "model": self.model_name, "dimension": len(vectors[0])},
        )
        return updated

    # ── Job description embedding ────────────────────────────────────────

    async def embed_job_description(self, job_description_id: uuid.UUID) -> JobDescription:
        """Embed a single JobDescription and persist the result."""
        jd = await self.job_description_repo.get_by_id(job_description_id)
        if jd is None:
            raise ValueError(f"JobDescription {job_description_id} not found.")
        if not jd.structured_json:
            raise ValueError(f"JobDescription {job_description_id} has no structured_json to embed.")

        text = normalize_text(
            build_job_description_embedding_text(jd.structured_json), max_chars=self.max_input_chars
        )

        await self.job_description_repo.update(jd, embedding_status=EmbeddingStatus.GENERATING)

        try:
            vectors = await self._encode([text])
        except ModelLoadError:
            await self.job_description_repo.update(jd, embedding_status=EmbeddingStatus.FAILED)
            raise

        vector = vectors[0]
        result = await self.job_description_repo.update(
            jd,
            embedding=vector,
            embedding_model=self.model_name,
            embedding_dimension=len(vector),
            embedding_generated_at=datetime.now(timezone.utc),
            embedding_status=EmbeddingStatus.READY,
        )
        logger.info(
            "Generated job description embedding",
            extra={
                "job_description_id": str(job_description_id),
                "model": self.model_name,
                "dimension": len(vector),
            },
        )
        return result

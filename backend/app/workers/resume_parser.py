"""
Celery task: parse_resume
─────────────────────────
Full parsing workflow for a single ResumeFile:

  Phase 1 — Fetch + mark PROCESSING (own DB transaction).
  Phase 2 — Extract raw text from the stored file (no DB).
  Phase 3 — POST text to AI service, receive structured JSON (no DB).
  Phase 4 — Upsert Candidate + ParsedResume, mark PARSED (own DB transaction).
  Phase 5 — Dispatch generate_resume_embedding (separate task, own retries).

Retry policy  : up to 3 retries with exponential back-off (30 s, 60 s, 120 s).
Permanent errors : ExtractionError and 4xx AI responses — no retry, status → FAILED.
Transient errors : 5xx AI responses and unexpected exceptions — retry up to limit.

Idempotency     : A resume already in PARSED state is silently skipped.
                  A retry that finds an existing ParsedResume updates it in place.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx
from celery import Task

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.campaign import Campaign
from app.models.resume_file import UploadStatus
from app.repositories.candidate import CandidateRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.resume_file import ResumeFileRepository
from app.services.resume_extraction import (
    ExtractionError,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_zip,
)
from app.workers.celery_app import celery_app
from app.workers.embedding_worker import generate_resume_embedding

logger = logging.getLogger(__name__)

_PARSER_VERSION = "v1"
_ZIP_MIME_TYPES = {
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}


# ── Private helpers ───────────────────────────────────────────────────────────


async def _get_campaign_org_id(session: Any, campaign_id: uuid.UUID) -> uuid.UUID | None:
    """Return org_id for a campaign without requiring the caller to know the org."""
    from sqlalchemy import select

    result = await session.execute(
        select(Campaign.org_id).where(
            Campaign.id == campaign_id,
            Campaign.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


async def _extract_text(storage_path: str, mime_type: str) -> str:
    file_path = str(Path(settings.LOCAL_STORAGE_PATH) / storage_path)
    if mime_type == "application/pdf":
        return await extract_text_from_pdf(file_path)
    if "wordprocessingml" in mime_type:
        return await extract_text_from_docx(file_path)
    if mime_type in _ZIP_MIME_TYPES:
        pairs = await extract_text_from_zip(file_path)
        return "\n\n".join(text for _, text in pairs)
    raise ExtractionError(f"Unsupported MIME type for extraction: '{mime_type}'")


async def _call_ai_service(
    text: str,
    *,
    _client: httpx.AsyncClient | None = None,
) -> dict:
    """POST extracted text to the AI parsing endpoint; returns the structured JSON."""

    async def _request(client: httpx.AsyncClient) -> dict:
        resp = await client.post(
            f"{settings.AI_SERVICE_URL}/parse-resume",
            json={"resume_text": text, "parser_version": _PARSER_VERSION},
        )
        resp.raise_for_status()
        return resp.json()

    if _client is not None:
        return await _request(_client)
    async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
        return await _request(client)


def _candidate_kwargs(ai_data: dict) -> dict:
    return {
        "first_name": (ai_data.get("first_name") or "").strip() or "Unknown",
        "last_name": (ai_data.get("last_name") or "").strip() or "Unknown",
        "email": ai_data.get("email") or None,
        "phone": ai_data.get("phone") or None,
        "linkedin_url": ai_data.get("linkedin_url") or None,
        "github_url": ai_data.get("github_url") or None,
        "location": ai_data.get("location") or None,
        "years_of_experience": ai_data.get("years_of_experience"),
        "current_company": ai_data.get("current_company") or None,
        "current_role": ai_data.get("current_role") or None,
    }


# ── Core async implementation ─────────────────────────────────────────────────


def _enqueue_resume_embedding(parsed_resume_id: str) -> None:
    generate_resume_embedding.delay(parsed_resume_id)


async def _run_parse_resume(
    resume_file_id_str: str,
    *,
    _session_factory: Any = None,
    _http_client: httpx.AsyncClient | None = None,
    _embedding_dispatcher: Any = None,
) -> None:
    """Full parse workflow. Accepts optional overrides for testability."""
    factory = _session_factory or AsyncSessionLocal
    dispatch_embedding = _embedding_dispatcher or _enqueue_resume_embedding
    rf_id = uuid.UUID(resume_file_id_str)
    log_ctx = {"resume_file_id": resume_file_id_str}

    # ── Phase 1: Fetch + mark PROCESSING ─────────────────────────────────────
    async with factory() as session:
        rf_repo = ResumeFileRepository(session)
        rf = await rf_repo.get_by_id(rf_id)

        if rf is None:
            logger.warning("ResumeFile not found — nothing to do", extra=log_ctx)
            return

        if rf.upload_status == UploadStatus.PARSED:
            logger.info("ResumeFile already parsed — idempotent skip", extra=log_ctx)
            return

        logger.info(
            "Starting parse",
            extra={**log_ctx, "status": rf.upload_status.value, "mime_type": rf.mime_type},
        )
        await rf_repo.update(rf, upload_status=UploadStatus.PROCESSING, error_message=None)
        await session.commit()

        # Capture scalars before the session closes (expire_on_commit=False preserves them)
        campaign_id: uuid.UUID = rf.campaign_id
        storage_path: str = rf.storage_path
        mime_type: str = rf.mime_type

    # ── Phase 2: Extract text ─────────────────────────────────────────────────
    logger.info("Extracting text", extra={**log_ctx, "mime_type": mime_type})
    raw_text = await _extract_text(storage_path, mime_type)
    logger.info("Text extracted", extra={**log_ctx, "char_count": len(raw_text)})

    # ── Phase 3: Call AI service ──────────────────────────────────────────────
    logger.info(
        "Calling AI service",
        extra={**log_ctx, "url": settings.AI_SERVICE_URL},
    )
    ai_data = await _call_ai_service(raw_text, _client=_http_client)
    logger.info(
        "AI service response received",
        extra={**log_ctx, "keys": list(ai_data.keys())},
    )

    # ── Phase 4: Persist results ──────────────────────────────────────────────
    async with factory() as session:
        org_id = await _get_campaign_org_id(session, campaign_id)
        if org_id is None:
            raise RuntimeError(
                f"Campaign {campaign_id} not found — cannot determine org_id."
            )

        rf_repo = ResumeFileRepository(session)
        candidate_repo = CandidateRepository(session)
        parsed_repo = ParsedResumeRepository(session)

        # Upsert Candidate: match by email within the same org, otherwise create
        email = ai_data.get("email") or None
        candidate = None
        if email:
            candidate = await candidate_repo.find_by_email_and_org(email, org_id)
            if candidate:
                logger.info(
                    "Matched existing candidate by email",
                    extra={**log_ctx, "candidate_id": str(candidate.id)},
                )
        if candidate is None:
            candidate = await candidate_repo.create(
                organization_id=org_id,
                **_candidate_kwargs(ai_data),
            )
            logger.info(
                "Created new candidate",
                extra={**log_ctx, "candidate_id": str(candidate.id)},
            )
        else:
            await candidate_repo.update(candidate, **_candidate_kwargs(ai_data))
            logger.info(
                "Updated existing candidate",
                extra={**log_ctx, "candidate_id": str(candidate.id)},
            )

        # Upsert ParsedResume — safe to re-run on retry
        existing_pr = await parsed_repo.find_by_resume_file(rf_id)
        if existing_pr is None:
            parsed_resume = await parsed_repo.create(
                resume_file_id=rf_id,
                candidate_id=candidate.id,
                raw_text=raw_text,
                structured_json=ai_data,
                parser_version=_PARSER_VERSION,
            )
            logger.info("Created ParsedResume record", extra=log_ctx)
        else:
            parsed_resume = await parsed_repo.update(
                existing_pr,
                candidate_id=candidate.id,
                raw_text=raw_text,
                structured_json=ai_data,
                parser_version=_PARSER_VERSION,
            )
            logger.info("Updated existing ParsedResume (retry path)", extra=log_ctx)

        # Mark ResumeFile as PARSED and link the resolved candidate
        rf = await rf_repo.get_by_id(rf_id)
        await rf_repo.update(
            rf,
            upload_status=UploadStatus.PARSED,
            candidate_id=candidate.id,
            error_message=None,
        )
        await session.commit()
        logger.info("ResumeFile marked PARSED", extra=log_ctx)
        parsed_resume_id = parsed_resume.id

    # ── Phase 5: Dispatch embedding generation ───────────────────────────────
    dispatch_embedding(str(parsed_resume_id))
    logger.info("Dispatched embedding generation", extra={**log_ctx, "parsed_resume_id": str(parsed_resume_id)})


async def _mark_failed(
    resume_file_id_str: str,
    error: str,
    *,
    _session_factory: Any = None,
) -> None:
    """Best-effort: set ResumeFile status to FAILED with an error message."""
    factory = _session_factory or AsyncSessionLocal
    try:
        rf_id = uuid.UUID(resume_file_id_str)
        async with factory() as session:
            repo = ResumeFileRepository(session)
            rf = await repo.get_by_id(rf_id)
            if rf is not None:
                await repo.update(
                    rf,
                    upload_status=UploadStatus.FAILED,
                    error_message=error[:1000],
                )
            await session.commit()
    except Exception as exc:
        logger.error(
            "Could not persist FAILED status",
            extra={"resume_file_id": resume_file_id_str, "mark_error": str(exc)},
        )


# ── Celery task (sync entry point) ────────────────────────────────────────────


def _parse_resume_task(self: Task, resume_file_id: str) -> None:
    """
    Core task logic extracted from the decorator for direct testability.
    Classifies errors into: permanent (no retry) vs transient (retry with backoff).
    """
    log_ctx = {"resume_file_id": resume_file_id, "attempt": self.request.retries + 1}
    logger.info("Task started", extra=log_ctx)

    try:
        asyncio.run(_run_parse_resume(resume_file_id))
        logger.info("Task completed", extra=log_ctx)

    except ExtractionError as exc:
        # Permanent — a corrupted file won't become readable on retry
        logger.error("Extraction failed (permanent)", extra={**log_ctx, "error": str(exc)})
        asyncio.run(_mark_failed(resume_file_id, f"Extraction failed: {exc}"))
        raise  # Celery marks task as FAILURE

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code < 500:
            # 4xx — bad request or auth; retrying with the same payload won't help
            logger.error(
                "AI service rejected request (permanent)",
                extra={**log_ctx, "http_status": status_code},
            )
            asyncio.run(
                _mark_failed(resume_file_id, f"AI service {status_code}: {exc}")
            )
            raise  # no retry
        # 5xx — transient server-side error
        asyncio.run(_mark_failed(resume_file_id, f"AI service 5xx ({status_code})"))
        countdown = 30 * (2 ** self.request.retries)
        logger.warning(
            "AI service 5xx — retrying",
            extra={**log_ctx, "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        asyncio.run(_mark_failed(resume_file_id, str(exc)[:1000]))
        countdown = 30 * (2 ** self.request.retries)
        logger.exception(
            "Unexpected error — retrying",
            extra={**log_ctx, "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.resume_parser.parse_resume",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def parse_resume(self: Task, resume_file_id: str) -> None:
    """Entry point registered with Celery. Delegates to _parse_resume_task."""
    _parse_resume_task(self, resume_file_id)

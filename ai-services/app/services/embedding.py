"""
Embedding generation abstraction.

Supports OpenAI (text-embedding-3-large) and SentenceTransformers (local
fallback, no external API calls). Both providers implement the same
BaseEmbeddingProvider interface, so EmbeddingService — and any future
caller — never branches on provider identity. Adding a provider means
adding a class here and a branch in create_embedding_provider(); nothing
else changes.
"""

import abc
import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass

from app.core.config import EmbeddingProvider, Settings

logger = logging.getLogger(__name__)


class EmbeddingGenerationError(Exception):
    """Raised when an embedding could not be generated after all retries."""


@dataclass(frozen=True)
class EmbeddingResult:
    embedding: list[float]
    model: str
    dimension: int


class BaseEmbeddingProvider(abc.ABC):
    """Common interface for all embedding providers."""

    model_name: str

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, in the same order."""


# ── OpenAI ────────────────────────────────────────────────────────────────────


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str) -> None:
        import openai  # lazy import

        self._client = openai.AsyncOpenAI(api_key=api_key)
        self.model_name = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in resp.data]


# ── SentenceTransformers (local fallback) ───────────────────────────────────


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        from sentence_transformers import SentenceTransformer  # lazy import

        self._model = SentenceTransformer(model)
        self.model_name = model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, convert_to_numpy=True)
        return [vector.tolist() for vector in vectors]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self._encode, texts)


# ── Factory ───────────────────────────────────────────────────────────────────


def create_embedding_provider(settings: Settings) -> BaseEmbeddingProvider:
    if settings.EMBEDDING_PROVIDER == EmbeddingProvider.openai:
        logger.info(
            "Embedding provider: OpenAI", extra={"model": settings.OPENAI_EMBEDDING_MODEL}
        )
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )

    logger.info(
        "Embedding provider: SentenceTransformers",
        extra={"model": settings.SENTENCE_TRANSFORMERS_MODEL},
    )
    return SentenceTransformerEmbeddingProvider(model=settings.SENTENCE_TRANSFORMERS_MODEL)


# ── Text normalization ───────────────────────────────────────────────────────


def normalize_text(text: str, *, max_chars: int = 8000) -> str:
    """
    Normalize text before embedding: Unicode NFKC normalize, collapse
    consecutive whitespace/newlines to single spaces, strip, and cap length
    so a single document can't blow past the provider's token limit.
    """
    normalized = unicodedata.normalize("NFKC", text)
    collapsed = re.sub(r"\s+", " ", normalized).strip()
    return collapsed[:max_chars]


# ── Embedding service ─────────────────────────────────────────────────────────


class EmbeddingService:
    """
    Provider-agnostic embedding generation with text normalization and retry.

    Callers only interact with generate_embedding() / generate_embeddings();
    swapping providers — or adding a new one to the factory above — requires
    no change here or in any caller.
    """

    def __init__(
        self,
        provider: BaseEmbeddingProvider,
        *,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        max_input_chars: int = 8000,
    ) -> None:
        self._provider = provider
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._max_input_chars = max_input_chars

    async def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._provider.embed(texts)
            except Exception as exc:  # provider SDKs each raise their own exception types
                last_exc = exc
                if attempt == self._max_retries:
                    break
                backoff = self._backoff_seconds * (2**attempt)
                logger.warning(
                    "Embedding call failed — retrying",
                    extra={"attempt": attempt + 1, "backoff_s": backoff, "error": str(exc)},
                )
                await asyncio.sleep(backoff)
        raise EmbeddingGenerationError(
            f"Embedding generation failed after {self._max_retries + 1} attempts: {last_exc}"
        ) from last_exc

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """Normalize and embed a single text; returns the vector plus model name + dimension."""
        normalized = normalize_text(text, max_chars=self._max_input_chars)
        vectors = await self._embed_with_retry([normalized])
        vector = vectors[0]
        return EmbeddingResult(
            embedding=vector,
            model=self._provider.model_name,
            dimension=len(vector),
        )

    async def generate_embeddings(self, texts: list[str]) -> list[EmbeddingResult]:
        """Batch variant of generate_embedding — one provider call for all texts."""
        normalized = [normalize_text(t, max_chars=self._max_input_chars) for t in texts]
        vectors = await self._embed_with_retry(normalized)
        return [
            EmbeddingResult(embedding=v, model=self._provider.model_name, dimension=len(v))
            for v in vectors
        ]


# ── FastAPI dependency ────────────────────────────────────────────────────────

_singleton: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Return the module-level singleton; create it on first call."""
    global _singleton
    if _singleton is None:
        from app.core.config import settings

        provider = create_embedding_provider(settings)
        _singleton = EmbeddingService(
            provider,
            max_retries=settings.EMBEDDING_MAX_RETRIES,
            backoff_seconds=settings.EMBEDDING_RETRY_BACKOFF_SECONDS,
            max_input_chars=settings.EMBEDDING_MAX_INPUT_CHARS,
        )
    return _singleton

"""
LLM abstraction layer.

Supports Anthropic (default) and OpenAI. Switch providers via LLM_PROVIDER env var.
Both clients expose the same interface: async complete(prompt) -> str.

Provider libraries are imported lazily so the service starts even if only one
SDK is installed.
"""

import abc
import logging

from app.core.config import LLMProvider, Settings

logger = logging.getLogger(__name__)


class BaseLLMClient(abc.ABC):
    """Common interface for all LLM providers."""

    @abc.abstractmethod
    async def complete(self, prompt: str) -> str:
        """Send *prompt* as a single user turn; return the raw text response."""


# ── Anthropic ─────────────────────────────────────────────────────────────────


class AnthropicLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import anthropic  # lazy import

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, prompt: str) -> str:
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=(
                "You are a structured data extraction API. "
                "Respond with valid JSON only — no markdown, no explanation."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text


# ── OpenAI ────────────────────────────────────────────────────────────────────


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import openai  # lazy import

        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def complete(self, prompt: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a structured data extraction API. Respond with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content


# ── Factory ───────────────────────────────────────────────────────────────────


def create_llm_client(settings: Settings) -> BaseLLMClient:
    if settings.LLM_PROVIDER == LLMProvider.anthropic:
        logger.info(
            "LLM provider: Anthropic",
            extra={"model": settings.ANTHROPIC_MODEL},
        )
        return AnthropicLLMClient(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        )

    logger.info("LLM provider: OpenAI", extra={"model": settings.OPENAI_MODEL})
    return OpenAILLMClient(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
    )


# ── FastAPI dependency ────────────────────────────────────────────────────────

_singleton: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    """Return the module-level singleton; create it on first call."""
    global _singleton
    if _singleton is None:
        from app.core.config import settings

        _singleton = create_llm_client(settings)
    return _singleton

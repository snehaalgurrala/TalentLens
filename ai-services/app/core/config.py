from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    anthropic = "anthropic"
    openai = "openai"


class EmbeddingProvider(str, Enum):
    openai = "openai"
    sentence_transformers = "sentence_transformers"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── LLM provider selection ────────────────────────────────
    LLM_PROVIDER: LLMProvider = LLMProvider.anthropic

    # ── Anthropic ─────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_MAX_TOKENS: int = 2048

    # ── OpenAI ───────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 2048

    # ── Embeddings ────────────────────────────────────────────
    EMBEDDING_PROVIDER: EmbeddingProvider = EmbeddingProvider.openai
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_RETRY_BACKOFF_SECONDS: float = 1.0
    EMBEDDING_MAX_INPUT_CHARS: int = 8000


settings = Settings()

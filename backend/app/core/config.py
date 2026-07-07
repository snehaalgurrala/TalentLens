from typing import Any
from urllib.parse import quote

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True,
    )

    # ── App ───────────────────────────────────────────────────
    APP_ENV: str = "development"
    PROJECT_NAME: str = "TalentLens"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── CORS ──────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── PostgreSQL ────────────────────────────────────────────
    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "talentlens"
    POSTGRES_USER: str = "talentlens_user"
    POSTGRES_PASSWORD: str = "change-me-please"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str | None = None
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-use-a-long-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Storage ───────────────────────────────────────────────
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "storage/resumes"
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── ZIP archive safety limits (zip-bomb protection) ────────
    ZIP_MAX_ENTRIES: int = 100
    ZIP_MAX_UNCOMPRESSED_TOTAL_MB: int = 50
    ZIP_MAX_COMPRESSION_RATIO: int = 100

    # AI Service
    AI_SERVICE_URL: str = "http://ai-service:8001"
    AI_SERVICE_TIMEOUT: int = 30

    # ── Local embeddings (no external API calls) ─────────────────
    LOCAL_EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    LOCAL_EMBEDDING_DEVICE: str = "cpu"
    LOCAL_EMBEDDING_BATCH_SIZE: int = 16
    LOCAL_EMBEDDING_MAX_INPUT_CHARS: int = 8000

    # ── Speech AI — local Whisper transcription (no external API calls) ──
    WHISPER_MODEL_NAME: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_MODEL_CACHE_DIR: str | None = None
    WHISPER_MAX_AUDIO_SIZE_MB: int = 25

    # ── Communication Analysis — deterministic Read Aloud scoring (no LLM calls) ──
    # The product has exactly one Read Aloud reference sentence today, shown to
    # every candidate regardless of campaign (see
    # frontend/src/features/candidate-runner/mock-data.ts::readAloudSentence).
    # This mirrors that fixed sentence on the backend until a future sprint adds
    # per-campaign assessment content.
    READ_ALOUD_REFERENCE_SENTENCE: str = (
        "The quick brown fox jumps over the lazy dog while carrying a bag of "
        "documents to the office."
    )

    # ── Communication Analysis — deterministic Listen & Repeat scoring ────
    # (no LLM calls; semantic similarity via the local embedding model). The
    # product has exactly one Listen & Repeat reference sentence today, shown
    # to every candidate regardless of campaign (see
    # frontend/src/features/candidate-runner/mock-data.ts::listenRepeatSentence).
    LISTEN_REPEAT_REFERENCE_SENTENCE: str = (
        "Innovation distinguishes between a leader and a follower in every "
        "industry we serve."
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json

            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def assemble_urls(self) -> "Settings":
        if not self.DATABASE_URL:
            # URL-encode credentials — a raw '@' or ':' in the password would
            # otherwise be misparsed as the start of the host segment.
            user = quote(self.POSTGRES_USER, safe="")
            password = quote(self.POSTGRES_PASSWORD, safe="")
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{user}:{password}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        elif "asyncpg" not in self.DATABASE_URL:
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

        return self


settings = Settings()

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# Fixed sentinel row ID — must match alembic/versions/c3d4e5f6a7b8_*.py.
PLATFORM_AI_CONFIG_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")


class PlatformAIConfig(Base):
    """Platform-wide singleton (always exactly one row, at PLATFORM_AI_CONFIG_ID).
    SUPER_ADMIN-editable. LLM fields (llm_provider/llm_model/temperature/
    max_tokens/prompt_logging_enabled) are persisted config only — no live LLM
    integration exists in this codebase yet. embedding_model/similarity_threshold/
    reranking_enabled/explainable_ai_enabled have varying degrees of real
    runtime wiring; see PlatformAIConfigService for what's actually connected."""

    __tablename__ = "platform_ai_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="none", server_default="none")
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False, default="", server_default="")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7, server_default="0.7")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024, server_default="1024")
    prompt_logging_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    embedding_model: Mapped[str] = mapped_column(
        String(200), nullable=False, default="BAAI/bge-large-en-v1.5", server_default="BAAI/bge-large-en-v1.5"
    )
    similarity_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.3, server_default="0.3"
    )
    reranking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    explainable_ai_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    retention_policy_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=365, server_default="365"
    )
    retention_policy_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    updater: Mapped["User | None"] = relationship("User", lazy="raise")

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.embedding import EmbeddingStatus

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.user import User


class ParsingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        Enum(ParsingStatus, name="parsingstatus"),
        nullable=False,
        default=ParsingStatus.PENDING,
        server_default=ParsingStatus.PENDING.value,
    )
    parsing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_status: Mapped[EmbeddingStatus] = mapped_column(
        Enum(EmbeddingStatus, name="embeddingstatus"),
        nullable=False,
        default=EmbeddingStatus.PENDING,
        server_default=EmbeddingStatus.PENDING.value,
    )
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Unsized pgvector column: dimension varies by provider (see embedding_dimension).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="raise")
    creator: Mapped["User | None"] = relationship("User", lazy="raise")

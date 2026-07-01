import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.embedding import EmbeddingStatus

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.resume_file import ResumeFile


class ParsedResume(Base):
    __tablename__ = "parsed_resumes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resume_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resume_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
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

    resume_file: Mapped["ResumeFile"] = relationship("ResumeFile", lazy="raise")
    candidate: Mapped["Candidate"] = relationship("Candidate", lazy="raise")

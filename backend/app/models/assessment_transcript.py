import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_recording import AssessmentRecording
    from app.models.organization import Organization


class TranscriptStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AssessmentTranscript(Base):
    """Speech-to-text transcript for one AssessmentRecording, produced by the
    async transcribe_recording Celery pipeline (app.workers.speech_transcription).

    Kept separate from AssessmentRecording, which continues to store upload
    metadata only. No communication scoring, no transcript comparison — those
    are future-sprint concerns; this row only tracks the transcription job's
    state and result. organization_id is denormalized from the recording's
    owning session so org-scoped lookups (the read-only API endpoint) don't
    need to join through assessment_recordings -> assessment_sessions."""

    __tablename__ = "assessment_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recording_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_recordings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[TranscriptStatus] = mapped_column(
        Enum(TranscriptStatus, name="transcriptstatus"),
        nullable=False,
        default=TranscriptStatus.PENDING,
        server_default=TranscriptStatus.PENDING.value,
    )
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    recording: Mapped["AssessmentRecording"] = relationship("AssessmentRecording", lazy="raise")
    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_session import AssessmentSession


class RecordingType(str, enum.Enum):
    READ_ALOUD = "READ_ALOUD"
    LISTEN_REPEAT = "LISTEN_REPEAT"


class RecordingStatus(str, enum.Enum):
    # Metadata registered but the audio bytes haven't been uploaded yet.
    # AssessmentSessionService.upload_recording is what stores the bytes and
    # flips a row to UPLOADED (or leaves it PENDING/unwritten on failure).
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"


class AssessmentRecording(Base):
    """Metadata for one candidate recording (read-aloud / listen-and-repeat)
    in one session. No transcript, no AI score — those are future-sprint
    concerns. Upserted per (session_id, recording_type): a retake before
    final submit overwrites the prior metadata row rather than appending."""

    __tablename__ = "assessment_recordings"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "recording_type", name="uq_assessment_recordings_session_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recording_type: Mapped[RecordingType] = mapped_column(
        Enum(RecordingType, name="recordingtype"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus, name="recordingstatus"),
        nullable=False,
        default=RecordingStatus.PENDING,
        server_default=RecordingStatus.PENDING.value,
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["AssessmentSession"] = relationship("AssessmentSession", lazy="raise")

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_transcript import AssessmentTranscript
    from app.models.organization import Organization


class AnalysisType(str, enum.Enum):
    READ_ALOUD = "READ_ALOUD"
    LISTEN_REPEAT = "LISTEN_REPEAT"


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AssessmentAnalysis(Base):
    """Deterministic communication-metrics analysis of one AssessmentTranscript,
    produced by the async analyze_read_aloud / analyze_listen_repeat Celery
    pipelines (app.workers.communication_analysis). No aptitude scoring, no
    LLM calls anywhere in this pipeline; comparison and scoring are pure
    deterministic text/embedding processing (app.ai.communication).

    word_accuracy/reading_speed_wpm/*_words are Read Aloud-specific and stay
    null on LISTEN_REPEAT rows; semantic_similarity/keyword_coverage are
    Listen & Repeat-specific and stay null on READ_ALOUD rows.
    overall_score/completion_percentage/analysis_json are shared by both
    analysis_type values.

    organization_id is denormalized from the transcript (itself denormalized
    from the recording's owning session), same rationale as
    AssessmentTranscript.organization_id: org-scoped lookups avoid joining
    through assessment_transcripts -> assessment_recordings ->
    assessment_sessions."""

    __tablename__ = "assessment_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_transcripts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType, name="analysistype"),
        nullable=False,
        default=AnalysisType.READ_ALOUD,
        server_default=AnalysisType.READ_ALOUD.value,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysisstatus"),
        nullable=False,
        default=AnalysisStatus.PENDING,
        server_default=AnalysisStatus.PENDING.value,
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    substituted_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_words: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_speed_wpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    keyword_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    transcript: Mapped["AssessmentTranscript"] = relationship("AssessmentTranscript", lazy="raise")
    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")

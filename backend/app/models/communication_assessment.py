import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_session import AssessmentSession
    from app.models.organization import Organization


class CommunicationAssessmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CommunicationAssessment(Base):
    """Recruiter-facing aggregate of one AssessmentSession's Read Aloud +
    Listen & Repeat AssessmentAnalysis rows, produced by the
    generate_communication_assessment Celery task
    (app.workers.communication_assessment) once both sibling analyses are
    COMPLETED. Deterministic scoring/rules only — no LLM calls anywhere in
    this pipeline (see app.ai.communication.communication_assessment_engine).

    Kept separate from AssessmentAnalysis: this table has at most one row per
    session (both analysis types feed into it), while AssessmentAnalysis has
    one row per transcript (one per recording/analysis type).

    organization_id is denormalized from the session (AssessmentSession.org_id)
    for the same org-scoped-lookup reason as AssessmentAnalysis.organization_id.
    """

    __tablename__ = "communication_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[CommunicationAssessmentStatus] = mapped_column(
        Enum(CommunicationAssessmentStatus, name="communicationassessmentstatus"),
        nullable=False,
        default=CommunicationAssessmentStatus.PENDING,
        server_default=CommunicationAssessmentStatus.PENDING.value,
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    listening_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    strengths_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    improvements_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    assessment_session: Mapped["AssessmentSession"] = relationship(
        "AssessmentSession", lazy="raise"
    )
    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")

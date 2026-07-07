import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.candidate import Candidate
    from app.models.organization import Organization


class AssessmentSection(str, enum.Enum):
    APTITUDE = "APTITUDE"
    READ_ALOUD = "READ_ALOUD"
    LISTEN_REPEAT = "LISTEN_REPEAT"


class AssessmentSessionStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class AssessmentSession(Base):
    """One candidate's attempt at a campaign's assessment. Aggregate root for
    AssessmentAnswer/AssessmentRecording — org_id lives here so every child
    row is scoped through session_id rather than duplicating org_id downward,
    same shape as CandidateTask/CandidateNote hanging off resume_file_id."""

    __tablename__ = "assessment_sessions"
    __table_args__ = (
        UniqueConstraint("campaign_id", "candidate_id", name="uq_assessment_sessions_campaign_candidate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_section: Mapped[AssessmentSection] = mapped_column(
        Enum(AssessmentSection, name="assessmentsection"),
        nullable=False,
        default=AssessmentSection.APTITUDE,
        server_default=AssessmentSection.APTITUDE.value,
    )
    # Only meaningful while current_section == APTITUDE (1-5); null once the
    # candidate has moved past the aptitude section.
    current_question: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[AssessmentSessionStatus] = mapped_column(
        Enum(AssessmentSessionStatus, name="assessmentsessionstatus"),
        nullable=False,
        default=AssessmentSessionStatus.IN_PROGRESS,
        server_default=AssessmentSessionStatus.IN_PROGRESS.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="raise")
    candidate: Mapped["Candidate"] = relationship("Candidate", lazy="raise")

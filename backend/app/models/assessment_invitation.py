import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assessment_session import AssessmentSession
    from app.models.campaign import Campaign
    from app.models.candidate import Candidate
    from app.models.organization import Organization


class AssessmentInvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    OPENED = "OPENED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class AssessmentInvitation(Base):
    """A candidate's emailed link to take one AssessmentSession. Only the
    SHA-256 hash of the access token is stored (same pattern as
    OrganizationInvitation.token_hash / User.refresh_token_hash) — the raw
    token is embedded in the emailed URL and never persisted.

    One row per AssessmentSession (unique constraint on
    assessment_session_id): resending an invitation updates the existing row
    with a fresh token/expiry rather than creating a second one.
    """

    __tablename__ = "assessment_invitations"

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
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[AssessmentInvitationStatus] = mapped_column(
        Enum(AssessmentInvitationStatus, name="assessmentinvitationstatus"),
        nullable=False,
        default=AssessmentInvitationStatus.PENDING,
        server_default=AssessmentInvitationStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")
    assessment_session: Mapped["AssessmentSession"] = relationship(
        "AssessmentSession", lazy="raise"
    )
    candidate: Mapped["Candidate"] = relationship("Candidate", lazy="raise")
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="raise")

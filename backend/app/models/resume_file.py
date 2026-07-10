import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.candidate import Candidate
    from app.models.user import User


class PipelineStage(str, enum.Enum):
    """Where a candidate's application sits in the recruiter's review pipeline.

    Loosely, not strictly, synced with the parsing pipeline: a few existing
    code paths that already set upload_status/review_status also nudge this
    field forward (APPLIED->PARSING when upload_status becomes PROCESSING;
    ->EMBEDDING->RANKED as parsing/embedding complete; ->SHORTLISTED/REJECTED
    when review_status changes). Those nudges are advisory only — recruiters
    can move this field to any value at any time via the pipeline-stage
    endpoint, and nothing enforces forward-only or sequential transitions.
    ASSESSMENT_SENT, INTERVIEW_SCHEDULED, and HIRED have no upstream signal
    and are set exclusively by recruiter action.
    """

    APPLIED = "APPLIED"
    PARSING = "PARSING"
    EMBEDDING = "EMBEDDING"
    RANKED = "RANKED"
    SHORTLISTED = "SHORTLISTED"
    ASSESSMENT_SENT = "ASSESSMENT_SENT"
    ASSESSMENT_IN_PROGRESS = "ASSESSMENT_IN_PROGRESS"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    REJECTED = "REJECTED"
    HIRED = "HIRED"
    ASSESSMENT_COMPLETED = "ASSESSMENT_COMPLETED"
    INTERVIEW_COMPLETED = "INTERVIEW_COMPLETED"
    OFFER_EXTENDED = "OFFER_EXTENDED"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    WITHDRAWN = "WITHDRAWN"
    ARCHIVED = "ARCHIVED"


_PIPELINE_STAGE_ORDER: dict[PipelineStage, int] = {
    PipelineStage.APPLIED: 0,
    PipelineStage.PARSING: 1,
    PipelineStage.EMBEDDING: 2,
    PipelineStage.RANKED: 3,
    PipelineStage.SHORTLISTED: 4,
    PipelineStage.ASSESSMENT_SENT: 5,
    # Candidate opened the assessment link — set automatically, between
    # ASSESSMENT_SENT and ASSESSMENT_COMPLETED (see PART 2 of the
    # phase5-sprint5.8-automatic-pipeline-workflow doc for the full
    # auto-transition list).
    PipelineStage.ASSESSMENT_IN_PROGRESS: 6,
    PipelineStage.INTERVIEW_SCHEDULED: 7,
    PipelineStage.REJECTED: 8,
    PipelineStage.HIRED: 9,
    # Appended, not interleaved: these stages have no upstream auto-nudge
    # signal (see is_earlier_pipeline_stage callers), so their relative
    # order here only matters for the terminal-most group at the end.
    PipelineStage.ASSESSMENT_COMPLETED: 10,
    PipelineStage.INTERVIEW_COMPLETED: 11,
    PipelineStage.OFFER_EXTENDED: 12,
    PipelineStage.OFFER_ACCEPTED: 13,
    PipelineStage.WITHDRAWN: 14,
    PipelineStage.ARCHIVED: 15,
}


def is_earlier_pipeline_stage(current: PipelineStage, candidate: PipelineStage) -> bool:
    """True if `current` precedes `candidate` in the advisory stage ordering.

    Used by the loose-sync nudges to avoid stepping a stage backward (e.g. a
    late-arriving PROCESSING signal shouldn't downgrade a candidate a
    recruiter already moved to SHORTLISTED).
    """
    return _PIPELINE_STAGE_ORDER[current] < _PIPELINE_STAGE_ORDER[candidate]


class UploadStatus(str, enum.Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PARSED = "PARSED"
    FAILED = "FAILED"


class ReviewStatus(str, enum.Enum):
    """A recruiter's hiring decision for this resume, distinct from
    UploadStatus (which only tracks the parsing pipeline). Nothing sets
    this to SHORTLISTED/REJECTED yet — that's a future recruiter-actions
    feature — but the dashboard reads it so those numbers become real the
    moment that feature lands."""

    PENDING = "PENDING"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"


class ResumeFile(Base):
    __tablename__ = "resume_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    upload_status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="uploadstatus"),
        nullable=False,
        default=UploadStatus.UPLOADED,
        server_default=UploadStatus.UPLOADED.value,
    )
    # Nullable so the row survives if the uploader is hard-deleted
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Set by the parsing pipeline after successful extraction
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Populated when upload_status == FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="reviewstatus"),
        nullable=False,
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pipeline_stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage, name="pipelinestage"),
        nullable=False,
        default=PipelineStage.APPLIED,
        server_default=PipelineStage.APPLIED.value,
    )
    assigned_recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="raise")
    uploader: Mapped["User | None"] = relationship(
        "User", foreign_keys=[uploaded_by], lazy="raise"
    )
    candidate: Mapped["Candidate | None"] = relationship("Candidate", lazy="raise")
    assigned_recruiter: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_recruiter_id], lazy="raise"
    )

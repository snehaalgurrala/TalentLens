import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.resume_file import ResumeFile
    from app.models.user import User


class ActivityEventType(str, enum.Enum):
    RESUME_UPLOADED = "RESUME_UPLOADED"
    PARSING_STARTED = "PARSING_STARTED"
    PARSED = "PARSED"
    PARSE_FAILED = "PARSE_FAILED"
    RANKED = "RANKED"
    VIEWED = "VIEWED"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    PIPELINE_STAGE_CHANGED = "PIPELINE_STAGE_CHANGED"
    RECRUITER_ASSIGNED = "RECRUITER_ASSIGNED"
    NOTE_ADDED = "NOTE_ADDED"
    ARCHIVED = "ARCHIVED"
    RESTORED = "RESTORED"
    TASK_CREATED = "TASK_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_REASSIGNED = "TASK_REASSIGNED"


class CandidateActivity(Base):
    __tablename__ = "candidate_activities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resume_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resume_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable — system-generated events (e.g. PARSED) have no acting user
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[ActivityEventType] = mapped_column(
        Enum(ActivityEventType, name="activityeventtype"), nullable=False
    )
    # Column named event_metadata (not `metadata`, which SQLAlchemy's
    # DeclarativeBase reserves for its own use); DB column stays "event_metadata" too.
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    resume_file: Mapped["ResumeFile"] = relationship("ResumeFile", lazy="raise")
    actor: Mapped["User | None"] = relationship("User", lazy="raise")

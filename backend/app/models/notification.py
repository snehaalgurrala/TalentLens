import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.resume_file import ResumeFile
    from app.models.user import User


class NotificationType(str, enum.Enum):
    """Mirrors frontend/src/types/notification.types.ts::NotificationType —
    keep both in sync."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Notification(Base):
    """A recruiter-facing notification, delivered live via the SSE stream in
    app.api.v1.endpoints.notifications (Redis pub/sub bridges the Celery
    worker process that creates most of these to the FastAPI process serving
    the stream) and persisted here so a client that wasn't connected at
    creation time still sees it on next load."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        # values_callable is required here: NotificationType's members
        # (INFO/SUCCESS/...) don't match their values (info/success/...,
        # lowercase, to mirror the frontend's NotificationType union) —
        # without it, SQLAlchemy's Enum type sends the member *name*
        # ("SUCCESS") to Postgres instead of the value ("success"), which
        # the native enum type (created with lowercase values) rejects.
        Enum(NotificationType, name="notificationtype", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=NotificationType.INFO,
        server_default=NotificationType.INFO.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional deep-link target — nullable since not every notification is
    # about a specific candidate.
    resume_file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("resume_files.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")
    user: Mapped["User"] = relationship("User", lazy="raise")
    resume_file: Mapped["ResumeFile | None"] = relationship("ResumeFile", lazy="raise")

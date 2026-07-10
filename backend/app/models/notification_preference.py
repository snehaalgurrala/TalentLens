import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

_TRUE = ("true",)


class NotificationPreference(Base):
    """Per-user singleton. Gates whether Notification-creating code paths
    (see NotificationPreferenceService.should_notify) create a row / send an
    email for a given event."""

    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    assessment_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    assessment_started: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    invitation_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    invitation_opened: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    candidate_shortlisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    ai_ranking_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    daily_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    weekly_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", lazy="raise")


# Event-name -> boolean-column-name mapping used by should_notify(); kept
# next to the model so both stay in sync with the actual columns above.
NOTIFICATION_EVENT_FIELDS: dict[str, str] = {
    "assessment_completed": "assessment_completed",
    "assessment_started": "assessment_started",
    "invitation_sent": "invitation_sent",
    "invitation_opened": "invitation_opened",
    "candidate_shortlisted": "candidate_shortlisted",
    "ai_ranking_completed": "ai_ranking_completed",
    "daily_summary": "daily_summary",
    "weekly_summary": "weekly_summary",
}

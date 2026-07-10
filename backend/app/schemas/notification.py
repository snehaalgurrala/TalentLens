from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    """Matches frontend/src/types/notification.types.ts::AppNotification —
    keep both in sync."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationUpdate(BaseModel):
    is_read: bool

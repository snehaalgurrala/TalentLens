import uuid

from app.models.notification_preference import (
    NOTIFICATION_EVENT_FIELDS,
    NotificationPreference,
)
from app.repositories.notification_preference import NotificationPreferenceRepository
from app.schemas.notification_preference import NotificationPreferenceUpdate

_DEFAULTS = {field: True for field in NOTIFICATION_EVENT_FIELDS.values()} | {
    "email_enabled": True,
    "in_app_enabled": True,
}


class NotificationPreferenceService:
    def __init__(self, repo: NotificationPreferenceRepository) -> None:
        self.repo = repo

    async def get_or_create(self, user_id: uuid.UUID) -> NotificationPreference:
        row = await self.repo.get_by_user(user_id)
        if row is None:
            row = await self.repo.create(user_id=user_id, **_DEFAULTS)
        return row

    async def update(
        self, user_id: uuid.UUID, data: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        row = await self.get_or_create(user_id)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row
        return await self.repo.update(row, **updates)


async def should_notify(
    repo: NotificationPreferenceRepository, user_id: uuid.UUID, event: str
) -> tuple[bool, bool]:
    """(in_app_allowed, email_allowed) for `event`. Callers that create a
    Notification row or send a notification email should check this first.

    Documented as the extensible pattern — see app/workers/communication_assessment.py
    for the one production call site wired to this today; not every
    notification-creating code path in the app calls this yet."""
    field = NOTIFICATION_EVENT_FIELDS.get(event)
    if field is None:
        # Unknown event name: fail open rather than silently swallowing a
        # notification for an event this mapping hasn't been taught about yet.
        return True, True

    prefs = await repo.get_by_user(user_id)
    if prefs is None:
        return True, True

    event_allowed = getattr(prefs, field)
    return (
        event_allowed and prefs.in_app_enabled,
        event_allowed and prefs.email_enabled,
    )

"""NotificationService — org-scoped CRUD over Notification rows, plus a
best-effort Redis Pub/Sub publish so a connected browser's SSE stream (see
app.api.v1.endpoints.notifications) gets the new notification the instant
it's created, with no polling.

Publishing is fire-and-forget: a Redis hiccup must never fail the caller's
real work (e.g. marking a communication assessment complete) just because a
notification couldn't be pushed live — the row is still persisted, so the
recipient sees it on their next page load either way.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationResponse

if TYPE_CHECKING:
    from app.repositories.notification import NotificationRepository

logger = logging.getLogger(__name__)

_CHANNEL_PREFIX = "notifications:"


def notification_channel(user_id: uuid.UUID) -> str:
    return f"{_CHANNEL_PREFIX}{user_id}"


async def _publish(user_id: uuid.UUID, notification: Notification) -> None:
    """Best-effort publish via a short-lived Redis connection — safe to call
    from both the FastAPI process and a Celery worker process, neither of
    which can rely on a shared, loop-bound Redis client the other could also
    reuse (see app.workers.celery_app.run_task's docstring on why a
    per-process singleton can't cross event loops)."""
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        try:
            payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
            await client.publish(notification_channel(user_id), json.dumps(payload))
        finally:
            await client.aclose()
    except Exception:
        logger.warning(
            "Failed to publish live notification — it is still persisted",
            extra={"user_id": str(user_id), "notification_id": str(notification.id)},
            exc_info=True,
        )


class NotificationService:
    def __init__(self, repo: NotificationRepository) -> None:
        self.repo = repo

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        message: str,
        resume_file_id: uuid.UUID | None = None,
    ) -> Notification:
        notification = await self.repo.create(
            organization_id=organization_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            resume_file_id=resume_file_id,
        )
        await _publish(user_id, notification)
        return notification

    async def list_for_user(self, user_id: uuid.UUID) -> list[Notification]:
        return await self.repo.list_by_user(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = await self.repo.get_by_id(notification_id)
        if notification is None or notification.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
            )
        return await self.repo.mark_read(notification)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        return await self.repo.mark_all_read(user_id)

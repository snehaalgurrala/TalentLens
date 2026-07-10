import uuid
from typing import Any

from sqlalchemy import func, select, update

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: Any) -> Notification:
        notification = Notification(**kwargs)
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID, *, limit: int = 50) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        return result.rowcount or 0

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
        )
        return result.scalar_one()

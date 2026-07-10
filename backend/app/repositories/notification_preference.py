import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_preference import NotificationPreference


class NotificationPreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user(self, user_id: uuid.UUID) -> NotificationPreference | None:
        result = await self.session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> NotificationPreference:
        row = NotificationPreference(**kwargs)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: NotificationPreference, **kwargs: Any) -> NotificationPreference:
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_email_config import PLATFORM_EMAIL_CONFIG_ID, PlatformEmailConfig


class PlatformEmailConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> PlatformEmailConfig:
        """The singleton row always exists post-migration (seeded at
        PLATFORM_EMAIL_CONFIG_ID)."""
        result = await self.session.execute(
            select(PlatformEmailConfig).where(PlatformEmailConfig.id == PLATFORM_EMAIL_CONFIG_ID)
        )
        return result.scalar_one()

    async def update(self, row: PlatformEmailConfig, **kwargs: Any) -> PlatformEmailConfig:
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform_ai_config import PLATFORM_AI_CONFIG_ID, PlatformAIConfig


class PlatformAIConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> PlatformAIConfig:
        """The singleton row always exists post-migration (seeded at
        PLATFORM_AI_CONFIG_ID)."""
        result = await self.session.execute(
            select(PlatformAIConfig).where(PlatformAIConfig.id == PLATFORM_AI_CONFIG_ID)
        )
        return result.scalar_one()

    async def update(self, row: PlatformAIConfig, **kwargs: Any) -> PlatformAIConfig:
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

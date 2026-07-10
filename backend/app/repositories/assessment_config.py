import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_config import AssessmentConfig


class AssessmentConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_org(self, org_id: uuid.UUID) -> AssessmentConfig | None:
        result = await self.session.execute(
            select(AssessmentConfig).where(AssessmentConfig.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> AssessmentConfig:
        row = AssessmentConfig(**kwargs)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def update(self, row: AssessmentConfig, **kwargs: Any) -> AssessmentConfig:
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

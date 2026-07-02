import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_description import JobDescription


class JobDescriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, job_description_id: uuid.UUID) -> JobDescription | None:
        result = await self.session.execute(
            select(JobDescription).where(
                JobDescription.id == job_description_id,
                JobDescription.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_campaign(self, campaign_id: uuid.UUID) -> list[JobDescription]:
        result = await self.session.execute(
            select(JobDescription)
            .where(
                JobDescription.campaign_id == campaign_id,
                JobDescription.is_deleted.is_(False),
            )
            .order_by(JobDescription.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> JobDescription:
        jd = JobDescription(**kwargs)
        self.session.add(jd)
        await self.session.flush()
        await self.session.refresh(jd)
        return jd

    async def update(self, job_description: JobDescription, **kwargs: Any) -> JobDescription:
        for key, value in kwargs.items():
            setattr(job_description, key, value)
        await self.session.flush()
        await self.session.refresh(job_description)
        return job_description

    async def soft_delete(self, job_description: JobDescription) -> None:
        job_description.is_deleted = True
        job_description.deleted_at = datetime.now(UTC)
        await self.session.flush()

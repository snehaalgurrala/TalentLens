import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume_file import ResumeFile


class ResumeFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, resume_id: uuid.UUID) -> ResumeFile | None:
        result = await self.session.execute(
            select(ResumeFile).where(
                ResumeFile.id == resume_id,
                ResumeFile.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_campaign(self, campaign_id: uuid.UUID) -> list[ResumeFile]:
        result = await self.session.execute(
            select(ResumeFile)
            .where(
                ResumeFile.campaign_id == campaign_id,
                ResumeFile.is_deleted.is_(False),
            )
            .order_by(ResumeFile.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ResumeFile:
        rf = ResumeFile(**kwargs)
        self.session.add(rf)
        await self.session.flush()
        await self.session.refresh(rf)
        return rf

    async def update(self, resume_file: ResumeFile, **kwargs: Any) -> ResumeFile:
        for key, value in kwargs.items():
            setattr(resume_file, key, value)
        await self.session.flush()
        await self.session.refresh(resume_file)
        return resume_file

    async def soft_delete(self, resume_file: ResumeFile) -> None:
        resume_file.is_deleted = True
        resume_file.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parsed_resume import ParsedResume


class ParsedResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, parsed_resume_id: uuid.UUID) -> ParsedResume | None:
        result = await self.session.execute(
            select(ParsedResume).where(ParsedResume.id == parsed_resume_id)
        )
        return result.scalar_one_or_none()

    async def find_by_resume_file(self, resume_file_id: uuid.UUID) -> ParsedResume | None:
        result = await self.session.execute(
            select(ParsedResume).where(ParsedResume.resume_file_id == resume_file_id)
        )
        return result.scalar_one_or_none()

    async def list_by_resume_file_ids(self, resume_file_ids: list[uuid.UUID]) -> list[ParsedResume]:
        if not resume_file_ids:
            return []
        result = await self.session.execute(
            select(ParsedResume).where(ParsedResume.resume_file_id.in_(resume_file_ids))
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ParsedResume:
        pr = ParsedResume(**kwargs)
        self.session.add(pr)
        await self.session.flush()
        await self.session.refresh(pr)
        return pr

    async def update(self, parsed_resume: ParsedResume, **kwargs: Any) -> ParsedResume:
        for key, value in kwargs.items():
            setattr(parsed_resume, key, value)
        await self.session.flush()
        await self.session.refresh(parsed_resume)
        return parsed_resume

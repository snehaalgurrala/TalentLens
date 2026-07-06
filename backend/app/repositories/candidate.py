import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_email_and_org(self, email: str, org_id: uuid.UUID) -> Candidate | None:
        result = await self.session.execute(
            select(Candidate).where(
                Candidate.email == email,
                Candidate.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_ids(self, candidate_ids: list[uuid.UUID]) -> list[Candidate]:
        if not candidate_ids:
            return []
        result = await self.session.execute(
            select(Candidate).where(Candidate.id.in_(candidate_ids))
        )
        return list(result.scalars().all())

    async def get_by_id_and_org(self, candidate_id: uuid.UUID, org_id: uuid.UUID) -> Candidate | None:
        result = await self.session.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> Candidate:
        candidate = Candidate(**kwargs)
        self.session.add(candidate)
        await self.session.flush()
        await self.session.refresh(candidate)
        return candidate

    async def update(self, candidate: Candidate, **kwargs: Any) -> Candidate:
        for key, value in kwargs.items():
            setattr(candidate, key, value)
        await self.session.flush()
        await self.session.refresh(candidate)
        return candidate

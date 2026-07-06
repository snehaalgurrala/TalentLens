import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_activity import ActivityEventType, CandidateActivity


class CandidateActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        resume_file_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        event_type: ActivityEventType,
        event_metadata: dict[str, Any] | None = None,
    ) -> CandidateActivity:
        activity = CandidateActivity(
            resume_file_id=resume_file_id,
            actor_id=actor_id,
            event_type=event_type,
            event_metadata=event_metadata,
        )
        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)
        return activity

    async def list_by_resume_file(self, resume_file_id: uuid.UUID) -> list[CandidateActivity]:
        result = await self.session.execute(
            select(CandidateActivity)
            .options(selectinload(CandidateActivity.actor))
            .where(CandidateActivity.resume_file_id == resume_file_id)
            .order_by(CandidateActivity.created_at.desc())
        )
        return list(result.scalars().all())

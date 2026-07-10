import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.assessment_session import AssessmentSession


class AssessmentSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, session_id: uuid.UUID, org_id: uuid.UUID) -> AssessmentSession | None:
        result = await self.session.execute(
            select(AssessmentSession).where(
                AssessmentSession.id == session_id,
                AssessmentSession.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_campaign_and_candidate(
        self, campaign_id: uuid.UUID, candidate_id: uuid.UUID, org_id: uuid.UUID
    ) -> AssessmentSession | None:
        result = await self.session.execute(
            select(AssessmentSession).where(
                AssessmentSession.campaign_id == campaign_id,
                AssessmentSession.candidate_id == candidate_id,
                AssessmentSession.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, org_id: uuid.UUID, campaign_id: uuid.UUID | None = None
    ) -> list[AssessmentSession]:
        """Eager-loads candidate/campaign (both lazy="raise" on the model) so
        callers can read session.candidate/session.campaign without a
        separate lookup per row."""
        query = (
            select(AssessmentSession)
            .options(joinedload(AssessmentSession.candidate), joinedload(AssessmentSession.campaign))
            .where(AssessmentSession.org_id == org_id)
        )
        if campaign_id is not None:
            query = query.where(AssessmentSession.campaign_id == campaign_id)
        query = query.order_by(AssessmentSession.started_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def create(self, **kwargs: Any) -> AssessmentSession:
        assessment_session = AssessmentSession(**kwargs)
        self.session.add(assessment_session)
        await self.session.flush()
        await self.session.refresh(assessment_session)
        return assessment_session

    async def update(self, assessment_session: AssessmentSession, **kwargs: Any) -> AssessmentSession:
        for key, value in kwargs.items():
            setattr(assessment_session, key, value)
        await self.session.flush()
        await self.session.refresh(assessment_session)
        return assessment_session

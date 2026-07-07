import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_analysis import AssessmentAnalysis


class AssessmentAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_transcript_id(self, transcript_id: uuid.UUID) -> AssessmentAnalysis | None:
        result = await self.session.execute(
            select(AssessmentAnalysis).where(AssessmentAnalysis.transcript_id == transcript_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, transcript_id: uuid.UUID, organization_id: uuid.UUID, **kwargs: Any
    ) -> AssessmentAnalysis:
        created = AssessmentAnalysis(
            transcript_id=transcript_id, organization_id=organization_id, **kwargs
        )
        self.session.add(created)
        await self.session.flush()
        await self.session.refresh(created)
        return created

    async def update(self, row: AssessmentAnalysis, **kwargs: Any) -> AssessmentAnalysis:
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

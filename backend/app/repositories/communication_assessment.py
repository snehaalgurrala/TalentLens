import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication_assessment import CommunicationAssessment


class CommunicationAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_session_id(
        self, assessment_session_id: uuid.UUID
    ) -> CommunicationAssessment | None:
        result = await self.session.execute(
            select(CommunicationAssessment).where(
                CommunicationAssessment.assessment_session_id == assessment_session_id
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, assessment_session_id: uuid.UUID, organization_id: uuid.UUID, **kwargs: Any
    ) -> CommunicationAssessment:
        created = CommunicationAssessment(
            assessment_session_id=assessment_session_id,
            organization_id=organization_id,
            **kwargs,
        )
        self.session.add(created)
        await self.session.flush()
        await self.session.refresh(created)
        return created

    async def update(self, row: CommunicationAssessment, **kwargs: Any) -> CommunicationAssessment:
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_transcript import AssessmentTranscript


class AssessmentTranscriptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_recording_id(self, recording_id: uuid.UUID) -> AssessmentTranscript | None:
        result = await self.session.execute(
            select(AssessmentTranscript).where(AssessmentTranscript.recording_id == recording_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, recording_id: uuid.UUID, organization_id: uuid.UUID, **kwargs: Any
    ) -> AssessmentTranscript:
        created = AssessmentTranscript(
            recording_id=recording_id, organization_id=organization_id, **kwargs
        )
        self.session.add(created)
        await self.session.flush()
        await self.session.refresh(created)
        return created

    async def update(self, row: AssessmentTranscript, **kwargs: Any) -> AssessmentTranscript:
        # Named `row`, not `transcript` — the model has its own `transcript`
        # text column, and callers pass transcript=... as a kwarg (see
        # AssessmentTranscriptService.complete_processing), which would
        # collide with a same-named positional parameter.
        for key, value in kwargs.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return row

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_recording import AssessmentRecording, RecordingType


class AssessmentRecordingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, recording_id: uuid.UUID) -> AssessmentRecording | None:
        result = await self.session.execute(
            select(AssessmentRecording).where(AssessmentRecording.id == recording_id)
        )
        return result.scalar_one_or_none()

    async def get_by_session_and_type(
        self, session_id: uuid.UUID, recording_type: RecordingType
    ) -> AssessmentRecording | None:
        result = await self.session.execute(
            select(AssessmentRecording).where(
                AssessmentRecording.session_id == session_id,
                AssessmentRecording.recording_type == recording_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> list[AssessmentRecording]:
        result = await self.session.execute(
            select(AssessmentRecording)
            .where(AssessmentRecording.session_id == session_id)
            .order_by(AssessmentRecording.created_at.asc())
        )
        return list(result.scalars().all())

    async def upsert(
        self, session_id: uuid.UUID, recording_type: RecordingType, **kwargs: Any
    ) -> AssessmentRecording:
        existing = await self.get_by_session_and_type(session_id, recording_type)
        if existing is not None:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        created = AssessmentRecording(
            session_id=session_id, recording_type=recording_type, **kwargs
        )
        self.session.add(created)
        await self.session.flush()
        await self.session.refresh(created)
        return created

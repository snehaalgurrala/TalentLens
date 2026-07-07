import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_answer import AssessmentAnswer


class AssessmentAnswerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_session_and_question(
        self, session_id: uuid.UUID, question_number: int
    ) -> AssessmentAnswer | None:
        result = await self.session.execute(
            select(AssessmentAnswer).where(
                AssessmentAnswer.session_id == session_id,
                AssessmentAnswer.question_number == question_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: uuid.UUID) -> list[AssessmentAnswer]:
        result = await self.session.execute(
            select(AssessmentAnswer)
            .where(AssessmentAnswer.session_id == session_id)
            .order_by(AssessmentAnswer.question_number.asc())
        )
        return list(result.scalars().all())

    async def upsert(
        self, session_id: uuid.UUID, question_number: int, answer: str
    ) -> AssessmentAnswer:
        existing = await self.get_by_session_and_question(session_id, question_number)
        if existing is not None:
            existing.answer = answer
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        created = AssessmentAnswer(
            session_id=session_id, question_number=question_number, answer=answer
        )
        self.session.add(created)
        await self.session.flush()
        await self.session.refresh(created)
        return created

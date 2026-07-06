import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_note import CandidateNote


class CandidateNoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_author(self, stmt: Any) -> Any:
        return stmt.options(selectinload(CandidateNote.author))

    async def get_by_id(self, note_id: uuid.UUID) -> CandidateNote | None:
        result = await self.session.execute(
            self._with_author(select(CandidateNote)).where(CandidateNote.id == note_id)
        )
        return result.scalar_one_or_none()

    async def list_by_resume_file(self, resume_file_id: uuid.UUID) -> list[CandidateNote]:
        result = await self.session.execute(
            self._with_author(select(CandidateNote))
            .where(CandidateNote.resume_file_id == resume_file_id)
            .order_by(CandidateNote.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> CandidateNote:
        note = CandidateNote(**kwargs)
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def update(self, note: CandidateNote, **kwargs: Any) -> CandidateNote:
        for key, value in kwargs.items():
            setattr(note, key, value)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def delete(self, note: CandidateNote) -> None:
        await self.session.delete(note)
        await self.session.flush()

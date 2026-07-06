import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate_task import CandidateTask


class CandidateTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _with_relations(self, stmt: Any) -> Any:
        return stmt.options(
            selectinload(CandidateTask.assignee), selectinload(CandidateTask.created_by)
        )

    async def get_by_id(self, task_id: uuid.UUID) -> CandidateTask | None:
        result = await self.session.execute(
            self._with_relations(select(CandidateTask)).where(CandidateTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_by_resume_file(self, resume_file_id: uuid.UUID) -> list[CandidateTask]:
        result = await self.session.execute(
            self._with_relations(select(CandidateTask))
            .where(CandidateTask.resume_file_id == resume_file_id)
            .order_by(
                CandidateTask.status.asc(),
                CandidateTask.due_date.asc().nulls_last(),
                CandidateTask.created_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> CandidateTask:
        task = CandidateTask(**kwargs)
        self.session.add(task)
        await self.session.flush()
        # A freshly constructed instance has never had assignee/created_by
        # loaded (lazy="raise"), so re-fetch with relations before returning
        # rather than refresh()-ing the bare row.
        loaded = await self.get_by_id(task.id)
        assert loaded is not None
        return loaded

    async def update(self, task: CandidateTask, **kwargs: Any) -> CandidateTask:
        for key, value in kwargs.items():
            setattr(task, key, value)
        await self.session.flush()
        # Reassign in particular changes assignee_id — re-fetch with
        # relations so the new assignee is loaded, not just the fresh column.
        loaded = await self.get_by_id(task.id)
        assert loaded is not None
        return loaded

    async def delete(self, task: CandidateTask) -> None:
        await self.session.delete(task)
        await self.session.flush()

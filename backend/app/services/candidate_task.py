"""CandidateTaskService — recruiter-created follow-up tasks on a candidate's
application (e.g. "Call candidate", "Schedule interview"). Modeled closely on
CandidateNoteService, but tasks are NOT author-locked: any recruiter-role org
member may edit/reassign/delete any task, consistent with the org-wide
(non-ownership-restricted) access model used across candidate management.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.candidate_activity import ActivityEventType
from app.models.candidate_task import TaskStatus
from app.services.candidate_lookup import resolve_resume_file

if TYPE_CHECKING:
    from app.models.candidate_task import CandidateTask
    from app.models.user import User
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.candidate_task import CandidateTaskRepository
    from app.repositories.resume_file import ResumeFileRepository
    from app.repositories.user import UserRepository
    from app.schemas.candidate_task import CandidateTaskCreate, CandidateTaskUpdate


class CandidateTaskService:
    def __init__(
        self,
        task_repo: CandidateTaskRepository,
        resume_file_repo: ResumeFileRepository,
        candidate_repo: CandidateRepository,
        campaign_repo: CampaignRepository,
        activity_repo: CandidateActivityRepository,
        user_repo: UserRepository,
    ) -> None:
        self.task_repo = task_repo
        self.resume_file_repo = resume_file_repo
        self.candidate_repo = candidate_repo
        self.campaign_repo = campaign_repo
        self.activity_repo = activity_repo
        self.user_repo = user_repo

    # ── Internal guards ──────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage candidate tasks.",
            )
        return user.org_id

    async def _resolve_resume_file_id(self, id_: uuid.UUID, user: User) -> uuid.UUID:
        org_id = self._require_org(user)
        rf = await resolve_resume_file(
            id_, org_id, self.resume_file_repo, self.candidate_repo, self.campaign_repo
        )
        return rf.id

    async def _get_task(self, task_id: uuid.UUID) -> CandidateTask:
        task = await self.task_repo.get_by_id(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
        return task

    async def _validate_assignee(self, assignee_id: uuid.UUID | None, user: User) -> None:
        if assignee_id is None:
            return
        assignee = await self.user_repo.get_by_id(assignee_id)
        if assignee is None or assignee.org_id != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assignee not found in your organization.",
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def list(self, id_: uuid.UUID, user: User) -> list[CandidateTask]:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        return await self.task_repo.list_by_resume_file(resume_file_id)

    async def create(
        self, id_: uuid.UUID, data: CandidateTaskCreate, user: User
    ) -> CandidateTask:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        await self._validate_assignee(data.assignee_id, user)
        task = await self.task_repo.create(
            resume_file_id=resume_file_id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            priority=data.priority,
            assignee_id=data.assignee_id,
            created_by_id=user.id,
        )
        await self.activity_repo.create(
            resume_file_id, user.id, ActivityEventType.TASK_CREATED, {"task_title": data.title}
        )
        return task

    async def update(
        self, id_: uuid.UUID, task_id: uuid.UUID, data: CandidateTaskUpdate, user: User
    ) -> CandidateTask:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        task = await self._get_task(task_id)
        fields = data.model_dump(exclude_unset=True)
        was_completed = task.status == TaskStatus.COMPLETED
        if fields.get("status") == TaskStatus.COMPLETED and not was_completed:
            fields["completed_at"] = datetime.now(UTC)
        elif "status" in fields and fields["status"] != TaskStatus.COMPLETED:
            fields["completed_at"] = None
        updated = await self.task_repo.update(task, **fields)
        if fields.get("status") == TaskStatus.COMPLETED and not was_completed:
            await self.activity_repo.create(
                resume_file_id,
                user.id,
                ActivityEventType.TASK_COMPLETED,
                {"task_title": updated.title},
            )
        return updated

    async def complete(self, id_: uuid.UUID, task_id: uuid.UUID, user: User) -> CandidateTask:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        task = await self._get_task(task_id)
        if task.status != TaskStatus.COMPLETED:
            task = await self.task_repo.update(
                task, status=TaskStatus.COMPLETED, completed_at=datetime.now(UTC)
            )
            await self.activity_repo.create(
                resume_file_id, user.id, ActivityEventType.TASK_COMPLETED, {"task_title": task.title}
            )
        return task

    async def reassign(
        self, id_: uuid.UUID, task_id: uuid.UUID, assignee_id: uuid.UUID | None, user: User
    ) -> CandidateTask:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        await self._validate_assignee(assignee_id, user)
        task = await self._get_task(task_id)
        previous_assignee_id = task.assignee_id
        updated = await self.task_repo.update(task, assignee_id=assignee_id)
        await self.activity_repo.create(
            resume_file_id,
            user.id,
            ActivityEventType.TASK_REASSIGNED,
            {
                "task_title": updated.title,
                "from_assignee_id": str(previous_assignee_id) if previous_assignee_id else None,
                "to_assignee_id": str(assignee_id) if assignee_id else None,
            },
        )
        return updated

    async def delete(self, id_: uuid.UUID, task_id: uuid.UUID, user: User) -> None:
        await self._resolve_resume_file_id(id_, user)
        task = await self._get_task(task_id)
        await self.task_repo.delete(task)

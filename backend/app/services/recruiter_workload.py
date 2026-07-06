"""RecruiterWorkloadService — ORG_ADMIN-only view of per-recruiter assigned
candidate counts, broken down by pipeline stage. Backed by a real SQL
GROUP BY aggregate (ResumeFileRepository.workload_by_org) rather than the
in-memory scan pattern used by CandidateManagementService's list endpoint.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.user import UserRole
from app.schemas.recruiter_workload import (
    RecruiterWorkloadItem,
    RecruiterWorkloadResponse,
    RecruiterWorkloadStageBreakdown,
)
from app.schemas.user import UserSummaryResponse

if TYPE_CHECKING:
    from app.models.resume_file import PipelineStage
    from app.models.user import User
    from app.repositories.resume_file import ResumeFileRepository
    from app.repositories.user import UserRepository


class RecruiterWorkloadService:
    def __init__(self, resume_file_repo: ResumeFileRepository, user_repo: UserRepository) -> None:
        self.resume_file_repo = resume_file_repo
        self.user_repo = user_repo

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view recruiter workload.",
            )
        return user.org_id

    async def get_workload(self, user: User) -> RecruiterWorkloadResponse:
        org_id = self._require_org(user)
        members = await self.user_repo.list_by_org(
            org_id, roles=[UserRole.ORG_ADMIN, UserRole.RECRUITER]
        )
        rows = await self.resume_file_repo.workload_by_org(org_id)

        by_recruiter: dict[uuid.UUID, dict[PipelineStage, int]] = {}
        for recruiter_id, stage, count in rows:
            by_recruiter.setdefault(recruiter_id, {})[stage] = count

        items = [
            RecruiterWorkloadItem(
                recruiter=UserSummaryResponse.model_validate(member),
                total_assigned=sum(by_recruiter.get(member.id, {}).values()),
                by_stage=[
                    RecruiterWorkloadStageBreakdown(pipeline_stage=stage, count=count)
                    for stage, count in by_recruiter.get(member.id, {}).items()
                ],
            )
            for member in members
        ]
        return RecruiterWorkloadResponse(items=items)

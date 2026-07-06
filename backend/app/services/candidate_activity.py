"""CandidateActivityService — read-only timeline for a single candidate."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.services.candidate_lookup import resolve_resume_file

if TYPE_CHECKING:
    from app.models.candidate_activity import CandidateActivity
    from app.models.user import User
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.resume_file import ResumeFileRepository


class CandidateActivityService:
    def __init__(
        self,
        activity_repo: CandidateActivityRepository,
        resume_file_repo: ResumeFileRepository,
        candidate_repo: CandidateRepository,
        campaign_repo: CampaignRepository,
    ) -> None:
        self.activity_repo = activity_repo
        self.resume_file_repo = resume_file_repo
        self.candidate_repo = candidate_repo
        self.campaign_repo = campaign_repo

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view candidate activity.",
            )
        return user.org_id

    async def _resolve_resume_file_id(self, id_: uuid.UUID, user: User) -> uuid.UUID:
        org_id = self._require_org(user)
        rf = await resolve_resume_file(
            id_, org_id, self.resume_file_repo, self.candidate_repo, self.campaign_repo
        )
        return rf.id

    async def list(self, id_: uuid.UUID, user: User) -> list[CandidateActivity]:
        resume_file_id = await self._resolve_resume_file_id(id_, user)
        return await self.activity_repo.list_by_resume_file(resume_file_id)

import uuid

from fastapi import HTTPException, status

from app.models.recruitment_settings import RecruitmentSettings
from app.models.user import User
from app.repositories.recruitment_settings import RecruitmentSettingsRepository
from app.schemas.recruitment_settings import RecruitmentSettingsUpdate

_DEFAULTS = {
    "default_resume_score_threshold": 60.0,
    "enable_explainable_ai": True,
    "max_resume_upload_count": 20,
    "max_resume_size_mb": 10,
    "supported_resume_formats": ["pdf", "doc", "docx"],
}


class RecruitmentSettingsService:
    def __init__(self, repo: RecruitmentSettingsRepository) -> None:
        self.repo = repo

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage recruitment settings.",
            )
        return user.org_id

    async def get_or_create(self, user: User) -> RecruitmentSettings:
        org_id = self._require_org(user)
        row = await self.repo.get_by_org(org_id)
        if row is None:
            row = await self.repo.create(org_id=org_id, **_DEFAULTS)
        return row

    async def update(self, data: RecruitmentSettingsUpdate, user: User) -> RecruitmentSettings:
        row = await self.get_or_create(user)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row
        return await self.repo.update(row, **updates)

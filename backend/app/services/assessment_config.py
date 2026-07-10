import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.assessment_config import AssessmentConfig
from app.models.user import User
from app.repositories.assessment_config import AssessmentConfigRepository
from app.schemas.assessment_config import AssessmentConfigUpdate


class AssessmentConfigService:
    def __init__(self, repo: AssessmentConfigRepository) -> None:
        self.repo = repo

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage assessment settings.",
            )
        return user.org_id

    async def get_or_create(self, user: User) -> AssessmentConfig:
        org_id = self._require_org(user)
        row = await self.repo.get_by_org(org_id)
        if row is None:
            row = await self.repo.create(
                org_id=org_id,
                read_aloud_reference_sentence=settings.READ_ALOUD_REFERENCE_SENTENCE,
                listen_repeat_reference_sentence=settings.LISTEN_REPEAT_REFERENCE_SENTENCE,
            )
        return row

    async def update(self, data: AssessmentConfigUpdate, user: User) -> AssessmentConfig:
        row = await self.get_or_create(user)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return row
        return await self.repo.update(row, **updates)

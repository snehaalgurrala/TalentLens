from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.recruitment_settings import RecruitmentSettingsRepository
from app.schemas.recruitment_settings import (
    RecruitmentSettingsResponse,
    RecruitmentSettingsUpdate,
)
from app.services.recruitment_settings import RecruitmentSettingsService

router = APIRouter()


def get_recruitment_settings_service(db: DBSession) -> RecruitmentSettingsService:
    return RecruitmentSettingsService(RecruitmentSettingsRepository(db))


RecruitmentSettingsServiceDep = Annotated[
    RecruitmentSettingsService, Depends(get_recruitment_settings_service)
]

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


@router.get(
    "",
    response_model=RecruitmentSettingsResponse,
    summary="Get the organization's recruitment/resume policy settings",
)
async def get_recruitment_settings(
    service: RecruitmentSettingsServiceDep,
    current_user: RecruiterUser,
) -> RecruitmentSettingsResponse:
    row = await service.get_or_create(current_user)
    return RecruitmentSettingsResponse.model_validate(row)


@router.patch(
    "",
    response_model=RecruitmentSettingsResponse,
    summary="Update the organization's recruitment/resume policy settings",
)
async def update_recruitment_settings(
    data: RecruitmentSettingsUpdate,
    service: RecruitmentSettingsServiceDep,
    current_user: AdminUser,
) -> RecruitmentSettingsResponse:
    row = await service.update(data, current_user)
    return RecruitmentSettingsResponse.model_validate(row)

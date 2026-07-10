from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.assessment_config import AssessmentConfigRepository
from app.schemas.assessment_config import AssessmentConfigResponse, AssessmentConfigUpdate
from app.services.assessment_config import AssessmentConfigService

router = APIRouter()


def get_assessment_config_service(db: DBSession) -> AssessmentConfigService:
    return AssessmentConfigService(AssessmentConfigRepository(db))


AssessmentConfigServiceDep = Annotated[
    AssessmentConfigService, Depends(get_assessment_config_service)
]

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


@router.get(
    "",
    response_model=AssessmentConfigResponse,
    summary="Get the organization's assessment content configuration",
)
async def get_assessment_config(
    service: AssessmentConfigServiceDep,
    current_user: RecruiterUser,
) -> AssessmentConfigResponse:
    row = await service.get_or_create(current_user)
    return AssessmentConfigResponse.model_validate(row)


@router.patch(
    "",
    response_model=AssessmentConfigResponse,
    summary="Update the organization's assessment content configuration",
)
async def update_assessment_config(
    data: AssessmentConfigUpdate,
    service: AssessmentConfigServiceDep,
    current_user: AdminUser,
) -> AssessmentConfigResponse:
    row = await service.update(data, current_user)
    return AssessmentConfigResponse.model_validate(row)

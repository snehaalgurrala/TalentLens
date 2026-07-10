from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.platform_ai_config import PlatformAIConfigRepository
from app.schemas.platform_ai_config import PlatformAIConfigResponse, PlatformAIConfigUpdate
from app.services.audit_log import AuditLogService
from app.services.platform_ai_config import PlatformAIConfigService

router = APIRouter()


def get_platform_ai_config_service(db: DBSession) -> PlatformAIConfigService:
    return PlatformAIConfigService(
        PlatformAIConfigRepository(db), AuditLogService(AuditLogRepository(db))
    )


PlatformAIConfigServiceDep = Annotated[
    PlatformAIConfigService, Depends(get_platform_ai_config_service)
]

_require_super_admin = RequireRoles(UserRole.SUPER_ADMIN)
SuperAdminUser = Annotated[User, Depends(_require_super_admin)]


@router.get(
    "",
    response_model=PlatformAIConfigResponse,
    summary="Get the platform-wide AI/embedding configuration",
    responses={403: {"description": "SUPER_ADMIN only."}},
)
async def get_platform_ai_config(
    service: PlatformAIConfigServiceDep,
    current_user: SuperAdminUser,
) -> PlatformAIConfigResponse:
    row = await service.get()
    return PlatformAIConfigResponse.model_validate(row)


@router.patch(
    "",
    response_model=PlatformAIConfigResponse,
    summary="Update the platform-wide AI/embedding configuration",
    responses={403: {"description": "SUPER_ADMIN only."}},
)
async def update_platform_ai_config(
    data: PlatformAIConfigUpdate,
    service: PlatformAIConfigServiceDep,
    current_user: SuperAdminUser,
) -> PlatformAIConfigResponse:
    return await service.update(data, current_user)

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.platform_email_config import PlatformEmailConfigRepository
from app.schemas.platform_email_config import (
    PlatformEmailConfigResponse,
    PlatformEmailConfigUpdate,
    SendTestEmailRequest,
    SendTestEmailResponse,
)
from app.services.audit_log import AuditLogService
from app.services.platform_email_config import PlatformEmailConfigService

router = APIRouter()


def get_platform_email_config_service(db: DBSession) -> PlatformEmailConfigService:
    return PlatformEmailConfigService(
        PlatformEmailConfigRepository(db), AuditLogService(AuditLogRepository(db))
    )


PlatformEmailConfigServiceDep = Annotated[
    PlatformEmailConfigService, Depends(get_platform_email_config_service)
]

_require_super_admin = RequireRoles(UserRole.SUPER_ADMIN)
SuperAdminUser = Annotated[User, Depends(_require_super_admin)]


@router.get(
    "",
    response_model=PlatformEmailConfigResponse,
    summary="Get the platform-wide SMTP configuration (password never returned)",
    responses={403: {"description": "SUPER_ADMIN only."}},
)
async def get_platform_email_config(
    service: PlatformEmailConfigServiceDep,
    current_user: SuperAdminUser,
) -> PlatformEmailConfigResponse:
    return await service.get()


@router.patch(
    "",
    response_model=PlatformEmailConfigResponse,
    summary="Update the platform-wide SMTP configuration",
    responses={403: {"description": "SUPER_ADMIN only."}},
)
async def update_platform_email_config(
    data: PlatformEmailConfigUpdate,
    service: PlatformEmailConfigServiceDep,
    current_user: SuperAdminUser,
) -> PlatformEmailConfigResponse:
    return await service.update(data, current_user)


@router.post(
    "/test",
    response_model=SendTestEmailResponse,
    summary="Send a test email using the current SMTP configuration",
    responses={
        200: {"description": "Result of the send attempt (success or failure, never raises)."},
        403: {"description": "SUPER_ADMIN only."},
    },
)
async def send_test_email(
    data: SendTestEmailRequest,
    service: PlatformEmailConfigServiceDep,
    current_user: SuperAdminUser,
) -> SendTestEmailResponse:
    return await service.send_test_email(data.to_email, current_user)

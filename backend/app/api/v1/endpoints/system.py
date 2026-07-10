from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import RequireRoles
from app.models.user import User, UserRole
from app.schemas.system_health import SystemHealthResponse
from app.services.system_health import SystemHealthService

router = APIRouter()

_require_super_admin = RequireRoles(UserRole.SUPER_ADMIN)
SuperAdminUser = Annotated[User, Depends(_require_super_admin)]


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Live system diagnostics: DB, Redis, Celery, Whisper, storage, disk, queue",
    responses={403: {"description": "SUPER_ADMIN only."}},
)
async def get_system_health(current_user: SuperAdminUser) -> SystemHealthResponse:
    return await SystemHealthService().get_report()

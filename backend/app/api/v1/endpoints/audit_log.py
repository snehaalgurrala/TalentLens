import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogListResponse
from app.services.audit_log import AuditLogService

router = APIRouter()

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


def get_audit_log_service(db: DBSession) -> AuditLogService:
    return AuditLogService(AuditLogRepository(db))


AuditLogServiceDep = Annotated[AuditLogService, Depends(get_audit_log_service)]


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit log entries (org-scoped; SUPER_ADMIN may pass org_id for cross-org view)",
)
async def list_audit_log(
    service: AuditLogServiceDep,
    current_user: AdminUser,
    org_id: uuid.UUID | None = Query(None),
    actor_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditLogListResponse:
    return await service.list(
        current_user,
        org_id=org_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

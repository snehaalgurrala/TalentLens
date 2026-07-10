from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.services.data_export import DataExportService

router = APIRouter()

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


def _require_org(current_user: User) -> None:
    if current_user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must belong to an organization to export data.",
        )


@router.get("/candidates.csv", summary="Export the organization's candidates as CSV")
async def export_candidates(db: DBSession, current_user: AdminUser) -> StreamingResponse:
    _require_org(current_user)
    service = DataExportService(db)
    return StreamingResponse(
        service.export_candidates_csv(current_user.org_id),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="candidates.csv"'},
    )


@router.get("/assessments.csv", summary="Export the organization's assessment sessions as CSV")
async def export_assessments(db: DBSession, current_user: AdminUser) -> StreamingResponse:
    _require_org(current_user)
    service = DataExportService(db)
    return StreamingResponse(
        service.export_assessments_csv(current_user.org_id),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="assessments.csv"'},
    )


@router.get("/audit-log.csv", summary="Export the organization's audit log as CSV")
async def export_audit_log(db: DBSession, current_user: AdminUser) -> StreamingResponse:
    _require_org(current_user)
    service = DataExportService(db)
    return StreamingResponse(
        service.export_audit_log_csv(current_user.org_id),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit-log.csv"'},
    )

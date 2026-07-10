from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.schemas.billing import BillingUsageResponse
from app.services.billing import BillingService

router = APIRouter()

_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


@router.get(
    "/usage",
    response_model=BillingUsageResponse,
    summary="Real, computed usage numbers for the caller's organization",
    responses={422: {"description": "User has no organization."}},
)
async def get_billing_usage(db: DBSession, current_user: AdminUser) -> BillingUsageResponse:
    if current_user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must belong to an organization to view billing usage.",
        )
    return await BillingService(db).get_usage(current_user.org_id, current_user)

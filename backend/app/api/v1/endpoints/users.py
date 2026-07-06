from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.user import UserRepository
from app.schemas.recruiter_workload import RecruiterWorkloadResponse
from app.schemas.user import UserResponse, UserSummaryResponse
from app.services.recruiter_workload import RecruiterWorkloadService

router = APIRouter()

# Workload exposes org-wide assignment counts; only admins manage staffing.
_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user's profile",
    responses={
        200: {"description": "Authenticated user's profile."},
        401: {"description": "Missing or invalid access token."},
        403: {"description": "Account is inactive."},
    },
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/org-members",
    response_model=list[UserSummaryResponse],
    summary="List assignable org members (for hiring manager / recruiter pickers)",
    responses={
        200: {"description": "Active ORG_ADMIN and RECRUITER accounts in the caller's org."},
        422: {"description": "User has no organization."},
    },
)
async def list_org_members(
    db: DBSession,
    current_user: CurrentUser,
) -> list[UserSummaryResponse]:
    if current_user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must belong to an organization to view members.",
        )
    members = await UserRepository(db).list_by_org(
        current_user.org_id, roles=[UserRole.ORG_ADMIN, UserRole.RECRUITER]
    )
    return [UserSummaryResponse.model_validate(m) for m in members]


@router.get(
    "/recruiter-workload",
    response_model=RecruiterWorkloadResponse,
    summary="Per-recruiter assigned-candidate counts, broken down by pipeline stage",
    responses={
        200: {"description": "Workload for every org member who can be assigned candidates."},
        403: {"description": "Insufficient role (only ORG_ADMIN/SUPER_ADMIN permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_recruiter_workload(
    db: DBSession,
    current_user: AdminUser,
) -> RecruiterWorkloadResponse:
    service = RecruiterWorkloadService(ResumeFileRepository(db), UserRepository(db))
    return await service.get_workload(current_user)

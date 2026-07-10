import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentSessionId, CurrentUser, DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.password_reset_token import PasswordResetTokenRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.recruiter_workload import RecruiterWorkloadResponse
from app.schemas.user import (
    ChangePasswordRequest,
    UserProfileUpdate,
    UserResponse,
    UserSummaryResponse,
)
from app.schemas.user_management import UserListItem, UserRoleUpdate
from app.services.audit_log import AuditLogService
from app.services.recruiter_workload import RecruiterWorkloadService
from app.services.user_management import UserManagementService
from app.services.user_profile import UserProfileService

router = APIRouter()

# Workload exposes org-wide assignment counts; only admins manage staffing.
_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]


def get_user_profile_service(db: DBSession) -> UserProfileService:
    return UserProfileService(UserRepository(db), UserSessionRepository(db))


def get_user_management_service(db: DBSession) -> UserManagementService:
    from app.repositories.audit_log import AuditLogRepository

    return UserManagementService(
        UserRepository(db),
        UserSessionRepository(db),
        PasswordResetTokenRepository(db),
        AuditLogService(AuditLogRepository(db)),
    )


UserProfileServiceDep = Annotated[UserProfileService, Depends(get_user_profile_service)]
UserManagementServiceDep = Annotated[UserManagementService, Depends(get_user_management_service)]


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


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the currently authenticated user's profile",
    responses={200: {"description": "Updated profile."}},
)
async def update_me(
    data: UserProfileUpdate,
    service: UserProfileServiceDep,
    current_user: CurrentUser,
) -> UserResponse:
    user = await service.update_profile(current_user, data)
    return UserResponse.model_validate(user)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the currently authenticated user's password",
    responses={
        204: {"description": "Password changed; other sessions revoked."},
        401: {"description": "Current password is incorrect."},
    },
)
async def change_my_password(
    data: ChangePasswordRequest,
    service: UserProfileServiceDep,
    current_user: CurrentUser,
    current_session_id: CurrentSessionId,
) -> None:
    await service.change_password(current_user, data, current_session_id)


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


# ── Admin: user management (Settings > Users) ──────────────────────────────

@router.get(
    "",
    response_model=list[UserListItem],
    summary="List every user in the caller's organization (any status)",
    responses={200: {"description": "All org users, active and inactive."}},
)
async def list_org_users(
    service: UserManagementServiceDep,
    current_user: AdminUser,
) -> list[UserListItem]:
    return await service.list_org_users(current_user)


@router.post(
    "/invite",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Invite a user to the caller's organization (delegates to POST /organizations/{org_id}/invitations)",
    responses={202: {"description": "Use POST /organizations/{org_id}/invitations instead."}},
)
async def invite_user_redirect(current_user: AdminUser) -> dict:
    return {
        "detail": (
            "Use POST /organizations/{org_id}/invitations "
            f"(org_id={current_user.org_id}) to invite a user."
        )
    }


@router.patch(
    "/{user_id}/role",
    response_model=UserListItem,
    summary="Change a user's role",
    responses={
        200: {"description": "Updated user."},
        403: {"description": "Cannot change own role or assign a role equal/higher than caller's."},
        404: {"description": "User not found."},
    },
)
async def update_user_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    service: UserManagementServiceDep,
    current_user: AdminUser,
) -> UserListItem:
    user = await service.update_role(current_user, user_id, data.role)
    return UserListItem.model_validate(user)


@router.post(
    "/{user_id}/deactivate",
    response_model=UserListItem,
    summary="Deactivate a user and revoke their active sessions",
    responses={
        200: {"description": "Deactivated user."},
        403: {"description": "Cannot deactivate own account."},
        404: {"description": "User not found."},
    },
)
async def deactivate_user(
    user_id: uuid.UUID,
    service: UserManagementServiceDep,
    current_user: AdminUser,
) -> UserListItem:
    user = await service.deactivate(current_user, user_id)
    return UserListItem.model_validate(user)


@router.post(
    "/{user_id}/reactivate",
    response_model=UserListItem,
    summary="Reactivate a deactivated user",
    responses={
        200: {"description": "Reactivated user."},
        404: {"description": "User not found."},
    },
)
async def reactivate_user(
    user_id: uuid.UUID,
    service: UserManagementServiceDep,
    current_user: AdminUser,
) -> UserListItem:
    user = await service.reactivate(current_user, user_id)
    return UserListItem.model_validate(user)


@router.post(
    "/{user_id}/reset-password",
    summary="Issue a password reset token for a user (raw token returned once)",
    responses={
        200: {"description": "Raw reset token — deliver it to the user out of band."},
        404: {"description": "User not found."},
    },
)
async def reset_user_password(
    user_id: uuid.UUID,
    service: UserManagementServiceDep,
    current_user: AdminUser,
) -> dict:
    token = await service.reset_password_admin(current_user, user_id)
    return {"token": token}

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.models.user import UserRole
from app.repositories.user import UserRepository
from app.schemas.user import UserResponse, UserSummaryResponse

router = APIRouter()


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

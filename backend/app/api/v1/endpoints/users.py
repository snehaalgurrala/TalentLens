from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.user import UserResponse

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

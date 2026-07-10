import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentSessionId, CurrentUser, DBSession
from app.repositories.user_session import UserSessionRepository
from app.schemas.user_session import UserSessionResponse
from app.services.user_session import UserSessionService

router = APIRouter()


def get_user_session_service(db: DBSession) -> UserSessionService:
    return UserSessionService(UserSessionRepository(db))


UserSessionServiceDep = Annotated[UserSessionService, Depends(get_user_session_service)]


@router.get(
    "/me",
    response_model=list[UserSessionResponse],
    summary="List the current user's active sessions/devices",
)
async def list_my_sessions(
    service: UserSessionServiceDep,
    current_user: CurrentUser,
    current_session_id: CurrentSessionId,
) -> list[UserSessionResponse]:
    return await service.list_active(current_user, current_session_id)


@router.delete(
    "/me/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke one of the current user's sessions (logs that device out)",
    responses={404: {"description": "Session not found or already revoked."}},
)
async def revoke_my_session(
    session_id: uuid.UUID,
    service: UserSessionServiceDep,
    current_user: CurrentUser,
) -> None:
    await service.revoke(current_user, session_id)


@router.post(
    "/me/revoke-others",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke every session except the one making this request",
)
async def revoke_other_sessions(
    service: UserSessionServiceDep,
    current_user: CurrentUser,
    current_session_id: CurrentSessionId,
) -> None:
    await service.revoke_all_others(current_user, current_session_id)

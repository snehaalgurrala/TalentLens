import uuid

from fastapi import HTTPException, Request, status

from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.user_session import UserSessionRepository
from app.schemas.auth import TokenResponse
from app.schemas.user_session import UserSessionResponse

_MAX_DEVICE_LABEL_LEN = 255


def _device_label_from_user_agent(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    return user_agent[:_MAX_DEVICE_LABEL_LEN]


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


class UserSessionService:
    def __init__(self, repo: UserSessionRepository) -> None:
        self.repo = repo

    def _make_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            org_id=str(user.org_id) if user.org_id else None,
        )
        refresh = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def create_session(
        self, user: User, request: Request | None = None
    ) -> tuple[UserSession, TokenResponse]:
        tokens = self._make_tokens(user)
        user_agent = request.headers.get("user-agent") if request else None
        session = await self.repo.create(
            user_id=user.id,
            refresh_token_hash=hash_token(tokens.refresh_token),
            device_label=_device_label_from_user_agent(user_agent),
            user_agent=user_agent,
            ip_address=_client_ip(request),
        )
        return session, tokens

    async def rotate(
        self, user: User, old_session: UserSession | None, request: Request | None = None
    ) -> tuple[UserSession, TokenResponse]:
        if old_session is not None:
            await self.repo.revoke(old_session)
        return await self.create_session(user, request)

    async def list_active(self, user: User, current_session_id: uuid.UUID | None) -> list[UserSessionResponse]:
        sessions = await self.repo.list_active_by_user(user.id)
        return [
            UserSessionResponse(
                id=s.id,
                device_label=s.device_label,
                user_agent=s.user_agent,
                ip_address=s.ip_address,
                created_at=s.created_at,
                last_seen_at=s.last_seen_at,
                is_current=(s.id == current_session_id),
            )
            for s in sessions
        ]

    async def revoke(self, user: User, session_id: uuid.UUID) -> None:
        session = await self.repo.get_by_id(session_id)
        if session is None or session.user_id != user.id or session.revoked_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        await self.repo.revoke(session)

    async def revoke_all_others(self, user: User, current_session_id: uuid.UUID | None) -> None:
        await self.repo.revoke_all_for_user(user.id, except_session_id=current_session_id)

    async def revoke_by_token_hash(self, token_hash: str) -> None:
        session = await self.repo.get_by_refresh_token_hash(token_hash)
        if session is not None and session.revoked_at is None:
            await self.repo.revoke(session)

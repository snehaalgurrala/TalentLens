import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

import jwt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user import UserRepository

# ── Database ──────────────────────────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Redis ─────────────────────────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield get_redis_client()


RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]


# ── Auth ──────────────────────────────────────────────────────────────────────
# tokenUrl is only used by the OpenAPI UI "Authorize" button; login is JSON-based.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    db: DBSession,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _CREDENTIALS_EXC
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise _CREDENTIALS_EXC

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )
    return user


# Annotated alias — use as a parameter type in any protected endpoint
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_session_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> uuid.UUID | None:
    """The UserSession.id embedded in the access token (see
    app.services.user_session), used to identify "this device" for the
    Security tab's session list and to exempt the calling device from
    change-password's revoke-all-other-sessions. None for tokens issued
    before session tracking existed (self-heals on next login/refresh)."""
    try:
        payload = decode_token(token)
        sid = payload.get("sid")
        return uuid.UUID(sid) if sid else None
    except (jwt.InvalidTokenError, ValueError):
        return None


CurrentSessionId = Annotated[uuid.UUID | None, Depends(get_current_session_id)]


# ── RBAC helper ───────────────────────────────────────────────────────────────
class RequireRoles:
    """Callable dependency that restricts access to the specified roles."""

    def __init__(self, *roles: UserRole) -> None:
        self.roles = set(roles)

    def __call__(self, user: CurrentUser) -> User:
        if user.role not in self.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

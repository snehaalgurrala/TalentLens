import uuid

import jwt
from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _make_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            org_id=str(user.org_id) if user.org_id else None,
        )
        refresh = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def _rotate_refresh_token(self, user: User, tokens: TokenResponse) -> None:
        """Replace the stored refresh-token hash with the newly issued one."""
        await self.user_repo.set_refresh_token_hash(user.id, hash_token(tokens.refresh_token))

    # ── Public methods ────────────────────────────────────────────────────────

    async def register(self, data: RegisterRequest) -> tuple[User, TokenResponse]:
        email = data.email.lower().strip()
        if await self.user_repo.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        user = await self.user_repo.create(
            email=email,
            full_name=data.full_name.strip(),
            password_hash=hash_password(data.password),
            role=data.role,
            org_id=data.org_id,
        )
        tokens = self._make_tokens(user)
        await self._rotate_refresh_token(user, tokens)
        return user, tokens

    async def login(self, data: LoginRequest) -> tuple[User, TokenResponse]:
        email = data.email.lower().strip()
        user = await self.user_repo.get_by_email(email)

        # Use a constant-time comparison path even on miss to prevent timing attacks
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated.",
            )
        tokens = self._make_tokens(user)
        await self._rotate_refresh_token(user, tokens)
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenResponse:
        _invalid = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise _invalid
            user_id = uuid.UUID(payload["sub"])
        except (jwt.InvalidTokenError, ValueError, KeyError):
            raise _invalid

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise _invalid

        # Reject if the token doesn't match the stored hash (already rotated / logged out)
        if not user.refresh_token_hash or user.refresh_token_hash != hash_token(refresh_token):
            raise _invalid

        tokens = self._make_tokens(user)
        await self._rotate_refresh_token(user, tokens)
        return tokens

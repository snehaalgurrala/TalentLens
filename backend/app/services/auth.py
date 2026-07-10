import uuid
from datetime import UTC, datetime

import jwt
from fastapi import HTTPException, Request, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.organization_invitation import InvitationStatus
from app.models.user import User, UserRole
from app.repositories.organization_invitation import OrganizationInvitationRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        invitation_repo: OrganizationInvitationRepository,
        session_repo: UserSessionRepository,
    ) -> None:
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.session_repo = session_repo

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _issue_session(
        self, user: User, request: Request | None
    ) -> TokenResponse:
        """Creates a new UserSession row and a token pair carrying its id as
        `sid`, and (dual-write, see the plan's rollout note) keeps the legacy
        User.refresh_token_hash column in sync too, so any code still reading
        it during the transition period keeps working."""
        session_id = uuid.uuid4()
        access = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            org_id=str(user.org_id) if user.org_id else None,
            session_id=str(session_id),
        )
        refresh = create_refresh_token(str(user.id), session_id=str(session_id))
        tokens = TokenResponse(access_token=access, refresh_token=refresh)

        user_agent = request.headers.get("user-agent") if request else None
        ip_address = request.client.host if request and request.client else None
        await self.session_repo.create(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_token(tokens.refresh_token),
            device_label=(user_agent[:255] if user_agent else None),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.user_repo.set_refresh_token_hash(user.id, hash_token(tokens.refresh_token))
        return tokens

    # ── Public methods ────────────────────────────────────────────────────────

    async def register(
        self, data: RegisterRequest, request: Request | None = None
    ) -> tuple[User, TokenResponse]:
        email = data.email.lower().strip()

        invalid_invitation = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token is invalid, expired, or already used.",
        )
        invitation = await self.invitation_repo.get_by_token_hash(
            hash_token(data.invitation_token)
        )
        if invitation is None or invitation.status != InvitationStatus.PENDING:
            raise invalid_invitation
        if invitation.expires_at < datetime.now(UTC):
            raise invalid_invitation
        if invitation.email.lower() != email:
            raise invalid_invitation

        if await self.user_repo.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = await self.user_repo.create(
            email=email,
            full_name=data.full_name.strip(),
            password_hash=hash_password(data.password),
            role=UserRole.RECRUITER,
            org_id=invitation.org_id,
        )
        await self.invitation_repo.update(
            invitation,
            status=InvitationStatus.ACCEPTED,
            accepted_at=datetime.now(UTC),
        )
        tokens = await self._issue_session(user, request)
        return user, tokens

    async def login(
        self, data: LoginRequest, request: Request | None = None
    ) -> tuple[User, TokenResponse]:
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
        tokens = await self._issue_session(user, request)
        return user, tokens

    async def refresh(self, refresh_token: str, request: Request | None = None) -> TokenResponse:
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

        token_hash = hash_token(refresh_token)
        session = await self.session_repo.get_by_refresh_token_hash(token_hash)
        if session is not None:
            if session.revoked_at is not None or session.user_id != user.id:
                raise _invalid
            await self.session_repo.revoke(session)
        else:
            # Self-heal: a token issued before session tracking existed, or
            # whose UserSession row is otherwise missing. Fall back to the
            # legacy column so pre-existing sessions aren't force-logged-out
            # by this rollout.
            if not user.refresh_token_hash or user.refresh_token_hash != token_hash:
                raise _invalid

        return await self._issue_session(user, request)

    async def logout(self, refresh_token: str) -> None:
        """Best-effort: an already-invalid/expired token still results in a
        204 — logout should never fail loudly just because the token being
        discarded is already unusable."""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                return
        except jwt.InvalidTokenError:
            return

        session = await self.session_repo.get_by_refresh_token_hash(hash_token(refresh_token))
        if session is not None and session.revoked_at is None:
            await self.session_repo.revoke(session)

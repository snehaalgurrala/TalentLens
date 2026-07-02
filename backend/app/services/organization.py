import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_invitation_token,
    hash_password,
    hash_token,
)
from app.models.organization import Organization
from app.models.organization_invitation import OrganizationInvitation
from app.models.user import User, UserRole
from app.repositories.organization import OrganizationRepository
from app.repositories.organization_invitation import OrganizationInvitationRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.organization import InvitationCreate, OrganizationBootstrapRequest

_INVITATION_EXPIRY_DAYS = 7


class OrganizationService:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        user_repo: UserRepository,
        invitation_repo: OrganizationInvitationRepository,
    ) -> None:
        self.org_repo = org_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo

    def _make_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
            org_id=str(user.org_id) if user.org_id else None,
        )
        refresh = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access, refresh_token=refresh)

    async def bootstrap(
        self, data: OrganizationBootstrapRequest
    ) -> tuple[Organization, User, TokenResponse]:
        """
        Create a brand-new organization plus its first ORG_ADMIN in one
        transaction. Always creates a fresh organization — it cannot be used
        to escalate privileges within an existing one.
        """
        if await self.org_repo.get_by_slug(data.org_slug):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An organization with this slug already exists.",
            )
        admin_email = data.admin_email.lower().strip()
        if await self.user_repo.get_by_email(admin_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        organization = await self.org_repo.create(
            name=data.org_name.strip(),
            slug=data.org_slug,
        )
        admin = await self.user_repo.create(
            email=admin_email,
            full_name=data.admin_full_name.strip(),
            password_hash=hash_password(data.admin_password),
            role=UserRole.ORG_ADMIN,
            org_id=organization.id,
        )
        tokens = self._make_tokens(admin)
        await self.user_repo.set_refresh_token_hash(admin.id, hash_token(tokens.refresh_token))
        return organization, admin, tokens

    async def invite(
        self, org_id: uuid.UUID, inviter: User, data: InvitationCreate
    ) -> tuple[OrganizationInvitation, str]:
        """Create a pending invitation; returns the row plus the raw (unhashed) token."""
        if inviter.role != UserRole.SUPER_ADMIN and inviter.org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to invite recruiters to this organization.",
            )
        organization = await self.org_repo.get_by_id(org_id)
        if organization is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        token = generate_invitation_token()
        invitation = await self.invitation_repo.create(
            org_id=org_id,
            email=data.email.lower().strip(),
            token_hash=hash_token(token),
            invited_by=inviter.id,
            expires_at=datetime.now(UTC) + timedelta(days=_INVITATION_EXPIRY_DAYS),
        )
        return invitation, token

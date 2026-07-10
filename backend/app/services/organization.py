import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
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
from app.schemas.organization import (
    InvitationCreate,
    OrganizationBootstrapRequest,
    OrganizationUpdate,
)
from app.services.audit_log import AuditLogService
from app.services.email.email_service import EmailService
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)

_INVITATION_EXPIRY_DAYS = 7
_MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024


class OrganizationService:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        user_repo: UserRepository,
        invitation_repo: OrganizationInvitationRepository,
        email_service: EmailService | None = None,
        storage: StorageBackend | None = None,
        audit_service: AuditLogService | None = None,
    ) -> None:
        self.audit_service = audit_service
        self.org_repo = org_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.email_service = email_service
        self.storage = storage

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
        expires_at = datetime.now(UTC) + timedelta(days=_INVITATION_EXPIRY_DAYS)
        invitation = await self.invitation_repo.create(
            org_id=org_id,
            email=data.email.lower().strip(),
            token_hash=hash_token(token),
            invited_by=inviter.id,
            expires_at=expires_at,
        )

        if self.audit_service is not None:
            await self.audit_service.record(
                org_id=org_id,
                actor_id=inviter.id,
                action="organization.invitation_sent",
                entity_type="organization_invitation",
                entity_id=invitation.id,
                metadata={"email": invitation.email},
            )

        if self.email_service is not None:
            registration_url = f"{settings.FRONTEND_BASE_URL}/register?token={token}"
            try:
                await self.email_service.send_organization_invitation(
                    to_email=invitation.email,
                    org_name=organization.name,
                    inviter_name=inviter.full_name,
                    registration_url=registration_url,
                    expires_at_display=expires_at.strftime("%B %d, %Y"),
                )
            except Exception as exc:
                # The invitation row is still created and its token still
                # valid even if the email couldn't be delivered — the
                # inviter sees the raw token in the response either way.
                logger.warning(
                    "Failed to send organization invitation email",
                    extra={"invitation_id": str(invitation.id), "error": str(exc)},
                    exc_info=True,
                )

        return invitation, token

    # ── Organization profile (Settings > Organization) ──────────────────────

    def _require_admin_of(self, org_id: uuid.UUID, user: User) -> None:
        if user.role != UserRole.SUPER_ADMIN and user.org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this organization.",
            )

    async def get_mine(self, user: User) -> Organization:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You do not belong to an organization.",
            )
        org = await self.org_repo.get_by_id(user.org_id)
        if org is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
        return org

    async def update_mine(self, data: OrganizationUpdate, user: User) -> Organization:
        org = await self.get_mine(user)
        self._require_admin_of(org.id, user)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return org
        updated = await self.org_repo.update(org, **updates)
        if self.audit_service is not None:
            await self.audit_service.record(
                org_id=org.id,
                actor_id=user.id,
                action="organization.updated",
                entity_type="organization",
                entity_id=org.id,
                metadata={"fields": list(updates.keys())},
            )
        return updated

    async def upload_logo(self, file: UploadFile, user: User) -> Organization:
        org = await self.get_mine(user)
        self._require_admin_of(org.id, user)
        if self.storage is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage backend is not configured.",
            )
        data = await file.read()
        if len(data) > _MAX_LOGO_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Logo file must be 5 MB or smaller.",
            )
        extension = (file.filename or "logo.png").rsplit(".", 1)[-1].lower()
        if extension not in {"png", "jpg", "jpeg", "svg", "webp"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Logo must be a PNG, JPG, SVG, or WEBP image.",
            )
        relative_path = f"org-logos/{org.id}.{extension}"
        storage_path = await self.storage.save(relative_path, data)
        return await self.org_repo.update(org, logo_url=storage_path)

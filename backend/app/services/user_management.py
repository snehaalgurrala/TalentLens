import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.core.security import generate_invitation_token, hash_token
from app.models.user import User, UserRole
from app.repositories.password_reset_token import PasswordResetTokenRepository
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.user_management import UserListItem
from app.services.audit_log import AuditLogService

_PASSWORD_RESET_EXPIRY_HOURS = 24

# Roles ordered from least to most privileged — used to stop an ORG_ADMIN
# from promoting someone past their own rank.
_ROLE_RANK: dict[UserRole, int] = {
    UserRole.CANDIDATE: 0,
    UserRole.RECRUITER: 1,
    UserRole.ORG_ADMIN: 2,
    UserRole.SUPER_ADMIN: 3,
}


class UserManagementService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: UserSessionRepository,
        reset_token_repo: PasswordResetTokenRepository,
        audit_service: AuditLogService,
    ) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.reset_token_repo = reset_token_repo
        self.audit_service = audit_service

    def _require_org(self, admin: User) -> uuid.UUID:
        if admin.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage users.",
            )
        return admin.org_id

    async def _require_target(self, admin: User, target_user_id: uuid.UUID) -> User:
        target = await self.user_repo.get_by_id(target_user_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        if admin.role != UserRole.SUPER_ADMIN and target.org_id != admin.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this user.",
            )
        return target

    async def list_org_users(self, admin: User) -> list[UserListItem]:
        org_id = self._require_org(admin)
        users = await self.user_repo.list_by_org_all_statuses(org_id)
        return [UserListItem.model_validate(u) for u in users]

    async def update_role(
        self, admin: User, target_user_id: uuid.UUID, new_role: UserRole
    ) -> User:
        if target_user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot change your own role.",
            )
        target = await self._require_target(admin, target_user_id)
        if admin.role != UserRole.SUPER_ADMIN and _ROLE_RANK[new_role] >= _ROLE_RANK[admin.role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot assign a role equal to or higher than your own.",
            )
        old_role = target.role
        updated = await self.user_repo.update(target, role=new_role)
        await self.audit_service.record(
            org_id=admin.org_id,
            actor_id=admin.id,
            action="user.role_changed",
            entity_type="user",
            entity_id=target.id,
            metadata={"old_role": old_role.value, "new_role": new_role.value},
        )
        return updated

    async def deactivate(self, admin: User, target_user_id: uuid.UUID) -> User:
        if target_user_id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot deactivate your own account.",
            )
        target = await self._require_target(admin, target_user_id)
        updated = await self.user_repo.update(target, is_active=False)
        await self.session_repo.revoke_all_for_user(target.id)
        await self.audit_service.record(
            org_id=admin.org_id,
            actor_id=admin.id,
            action="user.deactivated",
            entity_type="user",
            entity_id=target.id,
        )
        return updated

    async def reactivate(self, admin: User, target_user_id: uuid.UUID) -> User:
        target = await self._require_target(admin, target_user_id)
        updated = await self.user_repo.update(target, is_active=True)
        await self.audit_service.record(
            org_id=admin.org_id,
            actor_id=admin.id,
            action="user.reactivated",
            entity_type="user",
            entity_id=target.id,
        )
        return updated

    async def reset_password_admin(self, admin: User, target_user_id: uuid.UUID) -> str:
        """Issues a password-reset token for an existing user and returns the
        raw token (shown to the admin once, same pattern as invitation
        tokens) — actually emailing it is the caller's responsibility."""
        target = await self._require_target(admin, target_user_id)
        token = generate_invitation_token()
        await self.reset_token_repo.create(
            user_id=target.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=_PASSWORD_RESET_EXPIRY_HOURS),
        )
        await self.audit_service.record(
            org_id=admin.org_id,
            actor_id=admin.id,
            action="user.password_reset_issued",
            entity_type="user",
            entity_id=target.id,
        )
        return token

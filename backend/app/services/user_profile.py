import uuid

from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.user_session import UserSessionRepository
from app.schemas.user import ChangePasswordRequest, UserProfileUpdate


class UserProfileService:
    def __init__(self, user_repo: UserRepository, session_repo: UserSessionRepository) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return user
        return await self.user_repo.update(user, **updates)

    async def change_password(
        self, user: User, data: ChangePasswordRequest, current_session_id: uuid.UUID | None
    ) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )
        await self.user_repo.update(user, password_hash=hash_password(data.new_password))
        # Force re-login everywhere else — the device making this change
        # keeps its own session (it just proved possession of the old
        # password), every other device is logged out.
        await self.session_repo.revoke_all_for_user(user.id, except_session_id=current_session_id)

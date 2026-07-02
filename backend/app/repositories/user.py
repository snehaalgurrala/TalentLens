import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> User:
        user = User(**kwargs)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def set_refresh_token_hash(self, user_id: uuid.UUID, token_hash: str | None) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(refresh_token_hash=token_hash)
        )
        await self.session.flush()

    async def list_by_org(
        self, org_id: uuid.UUID, roles: list[UserRole] | None = None
    ) -> list[User]:
        stmt = (
            select(User)
            .where(User.org_id == org_id, User.is_active.is_(True))
            .order_by(User.full_name.asc())
        )
        if roles:
            stmt = stmt.where(User.role.in_(roles))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

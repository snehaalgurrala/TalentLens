import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession


class UserSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: Any) -> UserSession:
        row = UserSession(**kwargs)
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id(self, session_id: uuid.UUID) -> UserSession | None:
        result = await self.session.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_refresh_token_hash(self, token_hash: str) -> UserSession | None:
        result = await self.session.execute(
            select(UserSession).where(UserSession.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_active_by_user(self, user_id: uuid.UUID) -> list[UserSession]:
        result = await self.session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_seen_at.desc())
        )
        return list(result.scalars().all())

    async def touch_last_seen(self, session: UserSession) -> None:
        session.last_seen_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke(self, session: UserSession) -> None:
        session.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke_all_for_user(
        self, user_id: uuid.UUID, *, except_session_id: uuid.UUID | None = None
    ) -> None:
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        if except_session_id is not None:
            stmt = stmt.where(UserSession.id != except_session_id)
        await self.session.execute(stmt)
        await self.session.flush()

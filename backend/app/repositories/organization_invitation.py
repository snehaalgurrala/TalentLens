from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_invitation import OrganizationInvitation


class OrganizationInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        result = await self.session.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> OrganizationInvitation:
        invitation = OrganizationInvitation(**kwargs)
        self.session.add(invitation)
        await self.session.flush()
        await self.session.refresh(invitation)
        return invitation

    async def update(self, invitation: OrganizationInvitation, **kwargs: Any) -> OrganizationInvitation:
        for key, value in kwargs.items():
            setattr(invitation, key, value)
        await self.session.flush()
        await self.session.refresh(invitation)
        return invitation

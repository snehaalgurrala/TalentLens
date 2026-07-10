import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> Organization:
        organization = Organization(**kwargs)
        self.session.add(organization)
        await self.session.flush()
        await self.session.refresh(organization)
        return organization

    async def update(self, organization: Organization, **kwargs: Any) -> Organization:
        for key, value in kwargs.items():
            setattr(organization, key, value)
        await self.session.flush()
        await self.session.refresh(organization)
        return organization

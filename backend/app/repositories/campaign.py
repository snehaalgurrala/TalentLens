import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, campaign_id: uuid.UUID, org_id: uuid.UUID) -> Campaign | None:
        result = await self.session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.org_id == org_id,
                Campaign.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self, org_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> list[Campaign]:
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.org_id == org_id, Campaign.is_deleted.is_(False))
            .order_by(Campaign.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> Campaign:
        campaign = Campaign(**kwargs)
        self.session.add(campaign)
        await self.session.flush()
        await self.session.refresh(campaign)
        return campaign

    async def update(self, campaign: Campaign, **kwargs: Any) -> Campaign:
        for key, value in kwargs.items():
            setattr(campaign, key, value)
        await self.session.flush()
        await self.session.refresh(campaign)
        return campaign

    async def soft_delete(self, campaign: Campaign) -> None:
        campaign.is_deleted = True
        campaign.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

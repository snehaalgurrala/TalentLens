import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scoring_rule import ScoringRule


class ScoringRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_org_default(self, org_id: uuid.UUID) -> ScoringRule | None:
        result = await self.session.execute(
            select(ScoringRule).where(
                ScoringRule.org_id == org_id, ScoringRule.campaign_id.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_campaign_override(self, campaign_id: uuid.UUID) -> ScoringRule | None:
        result = await self.session.execute(
            select(ScoringRule).where(ScoringRule.campaign_id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs: Any) -> ScoringRule:
        rule = ScoringRule(**kwargs)
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def update(self, rule: ScoringRule, **kwargs: Any) -> ScoringRule:
        for key, value in kwargs.items():
            setattr(rule, key, value)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete(self, rule: ScoringRule) -> None:
        await self.session.delete(rule)
        await self.session.flush()

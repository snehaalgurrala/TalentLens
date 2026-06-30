import uuid

from fastapi import HTTPException, status

from app.models.campaign import Campaign
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignService:
    def __init__(self, repo: CampaignRepository) -> None:
        self.repo = repo

    # ── Internal guards ───────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage campaigns.",
            )
        return user.org_id

    def _assert_can_write(self, campaign: Campaign, user: User) -> None:
        """ORG_ADMIN and SUPER_ADMIN may edit any campaign; RECRUITERs only their own."""
        if user.role in {UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN}:
            return
        if campaign.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this campaign.",
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def create(self, data: CampaignCreate, user: User) -> Campaign:
        org_id = self._require_org(user)
        return await self.repo.create(
            org_id=org_id,
            created_by=user.id,
            title=data.title.strip(),
            description=data.description,
            status=data.status,
        )

    async def list_campaigns(
        self, user: User, *, skip: int = 0, limit: int = 50
    ) -> list[Campaign]:
        org_id = self._require_org(user)
        return await self.repo.list_by_org(org_id, skip=skip, limit=limit)

    async def get(self, campaign_id: uuid.UUID, user: User) -> Campaign:
        org_id = self._require_org(user)
        campaign = await self.repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return campaign

    async def update(
        self, campaign_id: uuid.UUID, data: CampaignUpdate, user: User
    ) -> Campaign:
        campaign = await self.get(campaign_id, user)
        self._assert_can_write(campaign, user)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return campaign
        return await self.repo.update(campaign, **updates)

    async def delete(self, campaign_id: uuid.UUID, user: User) -> None:
        campaign = await self.get(campaign_id, user)
        self._assert_can_write(campaign, user)
        await self.repo.soft_delete(campaign)

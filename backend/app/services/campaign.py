import uuid
from datetime import date

from fastapi import HTTPException, status

from app.models.campaign import Campaign, CampaignPriority, CampaignStatus, EmploymentType
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
        payload = data.model_dump()
        payload["title"] = payload["title"].strip()
        return await self.repo.create(org_id=org_id, created_by=user.id, **payload)

    async def list_campaigns(
        self,
        user: User,
        *,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        status_filter: CampaignStatus | None = None,
        department: str | None = None,
        employment_type: EmploymentType | None = None,
        priority: CampaignPriority | None = None,
        recruiter_id: uuid.UUID | None = None,
        hiring_manager_id: uuid.UUID | None = None,
        created_after: date | None = None,
        created_before: date | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> list[tuple[Campaign, int, int]]:
        org_id = self._require_org(user)
        return await self.repo.list_by_org_filtered(
            org_id,
            search=search,
            status=status_filter,
            department=department,
            employment_type=employment_type,
            priority=priority,
            recruiter_id=recruiter_id,
            hiring_manager_id=hiring_manager_id,
            created_after=created_after,
            created_before=created_before,
            sort_by=sort_by,
            sort_dir=sort_dir,
            skip=skip,
            limit=limit,
        )

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

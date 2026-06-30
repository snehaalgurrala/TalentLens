import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate
from app.services.campaign import CampaignService

router = APIRouter()

# ── Dependency factory (overridable in tests) ─────────────────────────────────

def get_campaign_service(db: DBSession) -> CampaignService:
    return CampaignService(CampaignRepository(db))


CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]

# Candidates cannot create, modify, or delete campaigns.
_require_write_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
WriteUser = Annotated[User, Depends(_require_write_role)]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recruitment campaign",
    responses={
        201: {"description": "Campaign created successfully."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "Validation error or user has no organization."},
    },
)
async def create_campaign(
    data: CampaignCreate,
    service: CampaignServiceDep,
    current_user: WriteUser,
) -> CampaignResponse:
    campaign = await service.create(data, current_user)
    return CampaignResponse.model_validate(campaign)


@router.get(
    "/",
    response_model=list[CampaignResponse],
    summary="List campaigns for the authenticated user's organization",
    responses={
        200: {"description": "Paginated list of active campaigns."},
        422: {"description": "User has no organization."},
    },
)
async def list_campaigns(
    service: CampaignServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
) -> list[CampaignResponse]:
    campaigns = await service.list_campaigns(current_user, skip=skip, limit=limit)
    return [CampaignResponse.model_validate(c) for c in campaigns]


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get a single campaign by ID",
    responses={
        200: {"description": "Campaign details."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def get_campaign(
    campaign_id: uuid.UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    campaign = await service.get(campaign_id, current_user)
    return CampaignResponse.model_validate(campaign)


@router.patch(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update a campaign (partial update)",
    responses={
        200: {"description": "Updated campaign."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found."},
    },
)
async def update_campaign(
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    service: CampaignServiceDep,
    current_user: WriteUser,
) -> CampaignResponse:
    campaign = await service.update(campaign_id, data, current_user)
    return CampaignResponse.model_validate(campaign)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a campaign",
    responses={
        204: {"description": "Campaign deleted (soft)."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found."},
    },
)
async def delete_campaign(
    campaign_id: uuid.UUID,
    service: CampaignServiceDep,
    current_user: WriteUser,
) -> None:
    await service.delete(campaign_id, current_user)

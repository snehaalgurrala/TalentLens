import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.schemas.scoring_rule import (
    EffectiveScoringRuleResponse,
    ScoringRuleCreate,
    ScoringRuleResponse,
    ScoringRuleUpdate,
)
from app.services.scoring_rule import ScoringRuleService

router = APIRouter()

# ── Dependency factory (overridable in tests) ─────────────────────────────────


def get_scoring_rule_service(db: DBSession) -> ScoringRuleService:
    return ScoringRuleService(ScoringRuleRepository(db), CampaignRepository(db))


ScoringRuleServiceDep = Annotated[ScoringRuleService, Depends(get_scoring_rule_service)]

# Organization-wide defaults are admin-controlled policy.
_require_admin_role = RequireRoles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
AdminUser = Annotated[User, Depends(_require_admin_role)]

# Campaign overrides (and all reads): recruiters and admins. Candidates have
# no legitimate use for internal scoring weights.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


# ── Organization default ─────────────────────────────────────────────────────

@router.post(
    "/organization",
    response_model=ScoringRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set the organization's default scoring rule",
    responses={
        201: {"description": "Organization scoring default created."},
        403: {"description": "Only ORG_ADMIN/SUPER_ADMIN may set organization-wide defaults."},
        409: {"description": "An organization scoring default already exists."},
        422: {"description": "Weights invalid, don't sum to 1.0, or user has no organization."},
    },
)
async def create_organization_default(
    data: ScoringRuleCreate,
    service: ScoringRuleServiceDep,
    current_user: AdminUser,
) -> ScoringRuleResponse:
    rule = await service.create_organization_default(data, current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.get(
    "/organization",
    response_model=ScoringRuleResponse,
    summary="Get the organization's default scoring rule",
    responses={
        200: {"description": "Organization scoring default."},
        404: {"description": "No organization scoring default configured."},
    },
)
async def get_organization_default(
    service: ScoringRuleServiceDep,
    current_user: RecruiterUser,
) -> ScoringRuleResponse:
    rule = await service.get_organization_default(current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.patch(
    "/organization",
    response_model=ScoringRuleResponse,
    summary="Update the organization's default scoring rule",
    responses={
        200: {"description": "Updated organization scoring default."},
        403: {"description": "Only ORG_ADMIN/SUPER_ADMIN may update organization-wide defaults."},
        404: {"description": "No organization scoring default configured."},
        422: {"description": "Weights invalid or don't sum to 1.0."},
    },
)
async def update_organization_default(
    data: ScoringRuleUpdate,
    service: ScoringRuleServiceDep,
    current_user: AdminUser,
) -> ScoringRuleResponse:
    rule = await service.update_organization_default(data, current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.delete(
    "/organization",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove the organization's default scoring rule",
    responses={
        204: {"description": "Organization scoring default removed."},
        403: {"description": "Only ORG_ADMIN/SUPER_ADMIN may remove organization-wide defaults."},
        404: {"description": "No organization scoring default configured."},
    },
)
async def delete_organization_default(
    service: ScoringRuleServiceDep,
    current_user: AdminUser,
) -> None:
    await service.delete_organization_default(current_user)


# ── Campaign override ─────────────────────────────────────────────────────────

@router.post(
    "/campaigns/{campaign_id}",
    response_model=ScoringRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set a scoring override for a campaign",
    responses={
        201: {"description": "Campaign scoring override created."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found."},
        409: {"description": "A scoring override already exists for this campaign."},
        422: {"description": "Weights invalid or don't sum to 1.0."},
    },
)
async def create_campaign_override(
    campaign_id: uuid.UUID,
    data: ScoringRuleCreate,
    service: ScoringRuleServiceDep,
    current_user: RecruiterUser,
) -> ScoringRuleResponse:
    rule = await service.create_campaign_override(campaign_id, data, current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.get(
    "/campaigns/{campaign_id}",
    response_model=ScoringRuleResponse,
    summary="Get a campaign's scoring override (raw, not resolved against the org default)",
    responses={
        200: {"description": "Campaign scoring override."},
        404: {"description": "Campaign not found or has no scoring override."},
    },
)
async def get_campaign_override(
    campaign_id: uuid.UUID,
    service: ScoringRuleServiceDep,
    current_user: RecruiterUser,
) -> ScoringRuleResponse:
    rule = await service.get_campaign_override(campaign_id, current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.patch(
    "/campaigns/{campaign_id}",
    response_model=ScoringRuleResponse,
    summary="Update a campaign's scoring override",
    responses={
        200: {"description": "Updated campaign scoring override."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found or has no scoring override."},
        422: {"description": "Weights invalid or don't sum to 1.0."},
    },
)
async def update_campaign_override(
    campaign_id: uuid.UUID,
    data: ScoringRuleUpdate,
    service: ScoringRuleServiceDep,
    current_user: RecruiterUser,
) -> ScoringRuleResponse:
    rule = await service.update_campaign_override(campaign_id, data, current_user)
    return ScoringRuleResponse.model_validate(rule)


@router.delete(
    "/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a campaign's scoring override",
    responses={
        204: {"description": "Campaign scoring override removed."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found or has no scoring override."},
    },
)
async def delete_campaign_override(
    campaign_id: uuid.UUID,
    service: ScoringRuleServiceDep,
    current_user: RecruiterUser,
) -> None:
    await service.delete_campaign_override(campaign_id, current_user)


@router.get(
    "/campaigns/{campaign_id}/effective",
    response_model=EffectiveScoringRuleResponse,
    summary="Get the scoring rule actually in effect for a campaign",
    responses={
        200: {
            "description": (
                "Resolved scoring rule: campaign override, else organization default, "
                "else the system default. `source` indicates which one was used."
            )
        },
        404: {"description": "Campaign not found."},
    },
)
async def get_effective_scoring_rule(
    campaign_id: uuid.UUID,
    service: ScoringRuleServiceDep,
    current_user: RecruiterUser,
) -> EffectiveScoringRuleResponse:
    return await service.get_effective(campaign_id, current_user)

import uuid
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, status

from app.models.scoring_rule import ScoringRule
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.schemas.scoring_rule import (
    MAX_PREFERRED_COMPANY_BONUS,
    SYSTEM_DEFAULT_WEIGHTS,
    EffectiveScoringRuleResponse,
    ScoringRuleCreate,
    ScoringRuleUpdate,
)


class _WeightedRule(Protocol):
    """Anything scoreable by compute_final_score: a persisted ScoringRule
    row or an EffectiveScoringRuleResponse (which may represent the
    unpersisted system default)."""

    semantic_weight: float
    skills_weight: float
    experience_weight: float
    education_weight: float
    project_weight: float
    certification_weight: float
    preferred_company_bonus: float
    preferred_companies: list[str]


@dataclass(frozen=True)
class ScoreBreakdown:
    """The pieces that make up compute_final_score's result, for callers
    (e.g. CandidateRankingService) that need to explain the number rather
    than just report it."""

    weighted_average: float
    bonus_points: float
    preferred_company_matched: bool
    final_score: float


def compute_score_breakdown(
    rule: _WeightedRule,
    *,
    semantic_score: float,
    skills_score: float,
    experience_score: float,
    education_score: float,
    project_score: float,
    certification_score: float,
    candidate_company: str | None = None,
) -> ScoreBreakdown:
    """Weighted average of the six sub-scores (each 0-100), plus a preferred-
    company bonus (in percentage points, hard-capped at 5 regardless of what
    the rule claims) if candidate_company is in the rule's preferred list."""
    weighted_average = (
        semantic_score * rule.semantic_weight
        + skills_score * rule.skills_weight
        + experience_score * rule.experience_weight
        + education_score * rule.education_weight
        + project_score * rule.project_weight
        + certification_score * rule.certification_weight
    )

    bonus_points = 0.0
    preferred_company_matched = False
    if candidate_company and rule.preferred_companies:
        candidate_key = candidate_company.strip().lower()
        preferred_keys = {c.strip().lower() for c in rule.preferred_companies}
        if candidate_key in preferred_keys:
            preferred_company_matched = True
            bonus_points = min(rule.preferred_company_bonus, MAX_PREFERRED_COMPANY_BONUS) * 100

    final_score = max(0.0, min(100.0, weighted_average + bonus_points))
    return ScoreBreakdown(
        weighted_average=weighted_average,
        bonus_points=bonus_points,
        preferred_company_matched=preferred_company_matched,
        final_score=final_score,
    )


def compute_final_score(
    rule: _WeightedRule,
    *,
    semantic_score: float,
    skills_score: float,
    experience_score: float,
    education_score: float,
    project_score: float,
    certification_score: float,
    candidate_company: str | None = None,
) -> float:
    """Convenience wrapper around compute_score_breakdown for callers that
    only need the final number."""
    return compute_score_breakdown(
        rule,
        semantic_score=semantic_score,
        skills_score=skills_score,
        experience_score=experience_score,
        education_score=education_score,
        project_score=project_score,
        certification_score=certification_score,
        candidate_company=candidate_company,
    ).final_score


def _rule_to_dict(rule: ScoringRule) -> dict:
    return {
        "id": rule.id,
        "org_id": rule.org_id,
        "campaign_id": rule.campaign_id,
        "created_by": rule.created_by,
        "semantic_weight": rule.semantic_weight,
        "skills_weight": rule.skills_weight,
        "experience_weight": rule.experience_weight,
        "education_weight": rule.education_weight,
        "project_weight": rule.project_weight,
        "certification_weight": rule.certification_weight,
        "preferred_company_bonus": rule.preferred_company_bonus,
        "preferred_companies": rule.preferred_companies,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


class ScoringRuleService:
    def __init__(self, repo: ScoringRuleRepository, campaign_repo: CampaignRepository) -> None:
        self.repo = repo
        self.campaign_repo = campaign_repo

    # ── Internal guards ───────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage scoring rules.",
            )
        return user.org_id

    async def _require_campaign(self, campaign_id: uuid.UUID, org_id: uuid.UUID):
        campaign = await self.campaign_repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return campaign

    def _assert_can_write_campaign_rule(self, campaign, user: User) -> None:
        """ORG_ADMIN and SUPER_ADMIN may edit any campaign's override; RECRUITERs only their own."""
        if user.role in {UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN}:
            return
        if campaign.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify scoring rules for this campaign.",
            )

    # ── Organization default ─────────────────────────────────────────────────

    async def create_organization_default(self, data: ScoringRuleCreate, user: User) -> ScoringRule:
        org_id = self._require_org(user)
        existing = await self.repo.get_org_default(org_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An organization scoring default already exists. Use PATCH to update it.",
            )
        return await self.repo.create(
            org_id=org_id, campaign_id=None, created_by=user.id, **data.model_dump()
        )

    async def get_organization_default(self, user: User) -> ScoringRule:
        org_id = self._require_org(user)
        rule = await self.repo.get_org_default(org_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No organization scoring default has been configured.",
            )
        return rule

    async def update_organization_default(self, data: ScoringRuleUpdate, user: User) -> ScoringRule:
        rule = await self.get_organization_default(user)
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return rule
        return await self.repo.update(rule, **updates)

    async def delete_organization_default(self, user: User) -> None:
        rule = await self.get_organization_default(user)
        await self.repo.delete(rule)

    # ── Campaign override ────────────────────────────────────────────────────

    async def create_campaign_override(
        self, campaign_id: uuid.UUID, data: ScoringRuleCreate, user: User
    ) -> ScoringRule:
        org_id = self._require_org(user)
        campaign = await self._require_campaign(campaign_id, org_id)
        self._assert_can_write_campaign_rule(campaign, user)
        existing = await self.repo.get_campaign_override(campaign_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A scoring override already exists for this campaign. Use PATCH to update it.",
            )
        return await self.repo.create(
            org_id=org_id, campaign_id=campaign_id, created_by=user.id, **data.model_dump()
        )

    async def get_campaign_override(self, campaign_id: uuid.UUID, user: User) -> ScoringRule:
        org_id = self._require_org(user)
        await self._require_campaign(campaign_id, org_id)
        rule = await self.repo.get_campaign_override(campaign_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No scoring override has been configured for this campaign.",
            )
        return rule

    async def update_campaign_override(
        self, campaign_id: uuid.UUID, data: ScoringRuleUpdate, user: User
    ) -> ScoringRule:
        org_id = self._require_org(user)
        campaign = await self._require_campaign(campaign_id, org_id)
        self._assert_can_write_campaign_rule(campaign, user)
        rule = await self.repo.get_campaign_override(campaign_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No scoring override has been configured for this campaign.",
            )
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return rule
        return await self.repo.update(rule, **updates)

    async def delete_campaign_override(self, campaign_id: uuid.UUID, user: User) -> None:
        org_id = self._require_org(user)
        campaign = await self._require_campaign(campaign_id, org_id)
        self._assert_can_write_campaign_rule(campaign, user)
        rule = await self.repo.get_campaign_override(campaign_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No scoring override has been configured for this campaign.",
            )
        await self.repo.delete(rule)

    # ── Effective resolution ─────────────────────────────────────────────────

    async def get_effective(
        self, campaign_id: uuid.UUID, user: User
    ) -> EffectiveScoringRuleResponse:
        """Resolve campaign override -> organization default -> system default."""
        org_id = self._require_org(user)
        await self._require_campaign(campaign_id, org_id)

        override = await self.repo.get_campaign_override(campaign_id)
        if override is not None:
            return EffectiveScoringRuleResponse.model_validate(
                {**_rule_to_dict(override), "source": "campaign_override"}
            )

        default = await self.repo.get_org_default(org_id)
        if default is not None:
            return EffectiveScoringRuleResponse.model_validate(
                {**_rule_to_dict(default), "source": "organization_default"}
            )

        return EffectiveScoringRuleResponse.model_validate(
            {
                "id": None,
                "org_id": org_id,
                "campaign_id": campaign_id,
                "created_by": None,
                **SYSTEM_DEFAULT_WEIGHTS,
                "preferred_company_bonus": 0.0,
                "preferred_companies": [],
                "source": "system_default",
                "created_at": None,
                "updated_at": None,
            }
        )

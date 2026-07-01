from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.matching_service import DEFAULT_WEIGHTS

# Recruiter-facing weight field names. Distinct from MatchingWeights'
# internal field names (e.g. "project_weight" here vs "projects_weight"
# there) — this is the persisted, API-facing contract.
WEIGHT_FIELDS: tuple[str, ...] = (
    "semantic_weight",
    "skills_weight",
    "experience_weight",
    "education_weight",
    "project_weight",
    "certification_weight",
)

WEIGHT_SUM_TOLERANCE = 0.001
MAX_PREFERRED_COMPANY_BONUS = 0.05

# Falls back to MatchingWeights' defaults so "no rule configured anywhere"
# behaves identically to today's un-configured matching engine.
SYSTEM_DEFAULT_WEIGHTS: dict[str, float] = {
    "semantic_weight": DEFAULT_WEIGHTS.semantic_weight,
    "skills_weight": DEFAULT_WEIGHTS.skills_weight,
    "experience_weight": DEFAULT_WEIGHTS.experience_weight,
    "education_weight": DEFAULT_WEIGHTS.education_weight,
    "project_weight": DEFAULT_WEIGHTS.projects_weight,
    "certification_weight": DEFAULT_WEIGHTS.certification_weight,
}


def _weight_sum_error(total: float) -> str:
    return (
        "semantic_weight + skills_weight + experience_weight + education_weight + "
        f"project_weight + certification_weight must sum to 1.0 (got {total:.4f})."
    )


class ScoringRuleCreate(BaseModel):
    semantic_weight: float = Field(SYSTEM_DEFAULT_WEIGHTS["semantic_weight"], ge=0.0, le=1.0)
    skills_weight: float = Field(SYSTEM_DEFAULT_WEIGHTS["skills_weight"], ge=0.0, le=1.0)
    experience_weight: float = Field(SYSTEM_DEFAULT_WEIGHTS["experience_weight"], ge=0.0, le=1.0)
    education_weight: float = Field(SYSTEM_DEFAULT_WEIGHTS["education_weight"], ge=0.0, le=1.0)
    project_weight: float = Field(SYSTEM_DEFAULT_WEIGHTS["project_weight"], ge=0.0, le=1.0)
    certification_weight: float = Field(
        SYSTEM_DEFAULT_WEIGHTS["certification_weight"], ge=0.0, le=1.0
    )
    preferred_company_bonus: float = Field(0.0, ge=0.0, le=MAX_PREFERRED_COMPANY_BONUS)
    preferred_companies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_weight_sum(self) -> "ScoringRuleCreate":
        total = sum(getattr(self, f) for f in WEIGHT_FIELDS)
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(_weight_sum_error(total))
        return self


class ScoringRuleUpdate(BaseModel):
    semantic_weight: float | None = Field(None, ge=0.0, le=1.0)
    skills_weight: float | None = Field(None, ge=0.0, le=1.0)
    experience_weight: float | None = Field(None, ge=0.0, le=1.0)
    education_weight: float | None = Field(None, ge=0.0, le=1.0)
    project_weight: float | None = Field(None, ge=0.0, le=1.0)
    certification_weight: float | None = Field(None, ge=0.0, le=1.0)
    preferred_company_bonus: float | None = Field(None, ge=0.0, le=MAX_PREFERRED_COMPANY_BONUS)
    preferred_companies: list[str] | None = None

    @model_validator(mode="after")
    def _validate_weight_sum(self) -> "ScoringRuleUpdate":
        provided = {f: getattr(self, f) for f in WEIGHT_FIELDS if getattr(self, f) is not None}
        if not provided:
            return self
        if len(provided) != len(WEIGHT_FIELDS):
            missing = [f for f in WEIGHT_FIELDS if f not in provided]
            raise ValueError(
                "To change scoring weights, all six weight fields must be provided together "
                f"so they can be validated to sum to 1.0. Missing: {', '.join(missing)}."
            )
        total = sum(provided.values())
        if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(_weight_sum_error(total))
        return self


class ScoringRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    campaign_id: UUID | None
    created_by: UUID | None
    semantic_weight: float
    skills_weight: float
    experience_weight: float
    education_weight: float
    project_weight: float
    certification_weight: float
    preferred_company_bonus: float
    preferred_companies: list[str]
    created_at: datetime
    updated_at: datetime


class EffectiveScoringRuleResponse(BaseModel):
    """The scoring rule actually in effect for a campaign, after resolving
    campaign override -> organization default -> system default."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID | None
    org_id: UUID
    campaign_id: UUID
    created_by: UUID | None
    semantic_weight: float
    skills_weight: float
    experience_weight: float
    education_weight: float
    project_weight: float
    certification_weight: float
    preferred_company_bonus: float
    preferred_companies: list[str]
    source: Literal["campaign_override", "organization_default", "system_default"]
    created_at: datetime | None = None
    updated_at: datetime | None = None

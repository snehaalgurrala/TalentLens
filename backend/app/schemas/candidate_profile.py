from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume_file import PipelineStage, ReviewStatus, UploadStatus
from app.schemas.candidate_ranking import RankingSubScores
from app.schemas.user import UserSummaryResponse

# ── Structured resume content (mirrors ai-services StructuredResume exactly —
# no fields invented beyond what the parser actually produces) ───────────────


class StructuredExperienceItem(BaseModel):
    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class StructuredEducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    graduation_year: str | None = None


class StructuredProjectItem(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class StructuredCertificationItem(BaseModel):
    name: str | None = None
    issuer: str | None = None
    date: str | None = None


class StructuredResumeContent(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: list[StructuredExperienceItem] = Field(default_factory=list)
    education: list[StructuredEducationItem] = Field(default_factory=list)
    projects: list[StructuredProjectItem] = Field(default_factory=list)
    certifications: list[StructuredCertificationItem] = Field(default_factory=list)
    summary: str | None = None


class CandidateProfileCampaign(BaseModel):
    id: UUID
    title: str


# ── Full profile ─────────────────────────────────────────────────────────────


class CandidateProfileResponse(BaseModel):
    resume_file_id: UUID
    candidate_id: UUID
    candidate_name: str
    email: str | None
    phone: str | None
    location: str | None
    linkedin_url: str | None
    github_url: str | None
    current_company: str | None
    current_role: str | None
    years_of_experience: float | None

    structured_resume: StructuredResumeContent
    parse_confidence: float | None

    campaign: CandidateProfileCampaign
    upload_status: UploadStatus
    review_status: ReviewStatus
    pipeline_stage: PipelineStage
    assigned_recruiter: UserSummaryResponse | None
    uploaded_at: datetime

    # Null until the campaign's job description has finished parsing/embedding
    # and this candidate has a ready embedding — never a fabricated score.
    overall_score: float | None = None
    sub_scores: RankingSubScores | None = None
    recommendation: (
        Literal["Strong Match", "Good Match", "Possible Match", "Not a Match"] | None
    ) = None
    ranking_available: bool


# ── AI match analysis (single candidate) ─────────────────────────────────────


class CandidateMatchAnalysisExplanationItem(BaseModel):
    text: str
    sentiment: Literal["positive", "negative", "neutral"]
    category: str


class CandidateMatchAnalysisResponse(BaseModel):
    overall_score: float
    recommendation: Literal["Strong Match", "Good Match", "Possible Match", "Not a Match"]
    sub_scores: RankingSubScores
    bonus_points: float
    preferred_company_matched: bool
    scoring_rule_source: Literal["campaign_override", "organization_default", "system_default"]
    match_explanation: str
    strengths: list[str]
    weaknesses: list[str]

    # Passthrough of MatchingService's own explanation detail dicts — these
    # are the single source of truth for match internals, so they're surfaced
    # as-is rather than re-modeled into a second parallel shape.
    semantic_details: dict[str, Any]
    skills_details: dict[str, Any]
    experience_details: dict[str, Any]
    education_details: dict[str, Any]
    projects_details: dict[str, Any]
    certification_details: dict[str, Any]

    explanation_items: list[CandidateMatchAnalysisExplanationItem]

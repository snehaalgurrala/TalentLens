from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.campaign import CampaignPriority, CampaignStatus, EmploymentType
from app.schemas.user import UserSummaryResponse


class CampaignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    status: CampaignStatus = CampaignStatus.DRAFT

    job_title: str | None = Field(None, max_length=255)
    department: str | None = Field(None, max_length=120)
    hiring_manager_id: UUID | None = None
    recruiter_id: UUID | None = None
    employment_type: EmploymentType | None = None
    location: str | None = Field(None, max_length=255)
    experience_min_years: int | None = Field(None, ge=0, le=60)
    experience_max_years: int | None = Field(None, ge=0, le=60)
    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)
    openings_count: int = Field(1, ge=1, le=1000)
    priority: CampaignPriority = CampaignPriority.MEDIUM
    closing_date: date | None = None


class CampaignUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: CampaignStatus | None = None

    job_title: str | None = Field(None, max_length=255)
    department: str | None = Field(None, max_length=120)
    hiring_manager_id: UUID | None = None
    recruiter_id: UUID | None = None
    employment_type: EmploymentType | None = None
    location: str | None = Field(None, max_length=255)
    experience_min_years: int | None = Field(None, ge=0, le=60)
    experience_max_years: int | None = Field(None, ge=0, le=60)
    salary_min: int | None = Field(None, ge=0)
    salary_max: int | None = Field(None, ge=0)
    openings_count: int | None = Field(None, ge=1, le=1000)
    priority: CampaignPriority | None = None
    closing_date: date | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    created_by: UUID | None
    title: str
    description: str | None
    status: CampaignStatus
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    job_title: str | None
    department: str | None
    hiring_manager_id: UUID | None
    recruiter_id: UUID | None
    employment_type: EmploymentType | None
    location: str | None
    experience_min_years: int | None
    experience_max_years: int | None
    salary_min: int | None
    salary_max: int | None
    openings_count: int
    priority: CampaignPriority
    closing_date: date | None

    hiring_manager: UserSummaryResponse | None = None
    recruiter: UserSummaryResponse | None = None
    resume_count: int = 0
    processing_resume_count: int = 0


class CampaignSummaryResponse(BaseModel):
    total_candidates: int
    processing_candidates: int
    ranked_candidates: int
    shortlisted_candidates: int
    rejected_candidates: int
    average_match_score: float | None


class CampaignProcessingStatusResponse(BaseModel):
    uploaded_count: int
    parsing_count: int
    embedding_count: int
    ready_for_ranking_count: int
    completed_count: int
    failed_count: int
    total_count: int

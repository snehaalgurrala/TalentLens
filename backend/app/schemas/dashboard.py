import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.campaign import CampaignStatus
from app.models.resume_file import ReviewStatus


class DashboardSummaryResponse(BaseModel):
    total_campaigns: int
    active_campaigns: int
    closed_campaigns: int
    total_candidates: int
    processing_candidates: int
    shortlisted_candidates: int
    rejected_candidates: int
    average_match_score: float | None


class RecentCampaignResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: CampaignStatus
    created_at: datetime
    candidate_count: int


class TopCandidateResponse(BaseModel):
    candidate_id: uuid.UUID
    candidate_name: str
    resume_file_id: uuid.UUID
    match_score: float
    campaign_id: uuid.UUID
    campaign_name: str
    years_of_experience: float | None
    current_company: str | None
    review_status: ReviewStatus


class ProcessingStatusResponse(BaseModel):
    parsing_queue: int
    embedding_queue: int
    ranking_queue: int
    failed_jobs: int
    completed_jobs: int


ActivityType = Literal[
    "CAMPAIGN_CREATED",
    "RESUME_UPLOADED",
    "CANDIDATE_SHORTLISTED",
    "CANDIDATE_REJECTED",
]


class ActivityItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: ActivityType
    description: str
    occurred_at: datetime
    campaign_id: uuid.UUID | None
    campaign_name: str | None

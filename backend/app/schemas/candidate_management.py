from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume_file import PipelineStage, ReviewStatus, UploadStatus
from app.schemas.candidate_ranking import RankingSubScores
from app.schemas.user import UserSummaryResponse


class EducationItem(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field: str | None = None


class CandidateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_file_id: UUID
    candidate_id: UUID
    candidate_name: str
    email: str | None
    phone: str | None
    location: str | None
    current_company: str | None
    current_role: str | None
    years_of_experience: float | None
    skills: list[str] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)

    # Ranking-derived — only populated when the campaign's job description
    # has finished parsing and embedding (see CandidateListResponse.ranking_available).
    rank: int | None = None
    overall_score: float | None = None
    sub_scores: RankingSubScores | None = None
    recommendation: Literal["Strong Match", "Good Match", "Possible Match", "Not a Match"] | None = None

    upload_status: UploadStatus
    review_status: ReviewStatus
    pipeline_stage: PipelineStage
    assigned_recruiter: UserSummaryResponse | None
    notes: str | None
    applied_at: datetime


class CandidateListResponse(BaseModel):
    items: list[CandidateListItem]
    total: int
    skip: int
    limit: int
    ranking_available: bool


class PipelineStageUpdate(BaseModel):
    pipeline_stage: PipelineStage


class RecruiterAssignmentUpdate(BaseModel):
    assigned_recruiter_id: UUID | None = None


class NotesUpdate(BaseModel):
    notes: str | None = Field(None, max_length=5000)


class BulkActionRequest(BaseModel):
    resume_file_ids: list[UUID] = Field(min_length=1, max_length=200)


class BulkAssignRecruiterRequest(BulkActionRequest):
    assigned_recruiter_id: UUID | None = None


class BulkPipelineStageRequest(BulkActionRequest):
    pipeline_stage: PipelineStage


class BulkActionFailure(BaseModel):
    id: UUID
    reason: str


class BulkActionResult(BaseModel):
    succeeded: list[UUID]
    failed: list[BulkActionFailure]

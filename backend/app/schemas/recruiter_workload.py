from pydantic import BaseModel

from app.models.resume_file import PipelineStage
from app.schemas.user import UserSummaryResponse


class RecruiterWorkloadStageBreakdown(BaseModel):
    pipeline_stage: PipelineStage
    count: int


class RecruiterWorkloadItem(BaseModel):
    recruiter: UserSummaryResponse
    total_assigned: int
    by_stage: list[RecruiterWorkloadStageBreakdown]


class RecruiterWorkloadResponse(BaseModel):
    items: list[RecruiterWorkloadItem]

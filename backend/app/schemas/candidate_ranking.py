from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.resume_file import ReviewStatus


class RankingSubScores(BaseModel):
    semantic_score: int
    skills_score: int
    experience_score: int
    education_score: int
    projects_score: int
    certification_score: int


class CandidateRankingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    candidate_id: UUID
    candidate_name: str
    resume_file_id: UUID
    overall_score: float
    sub_scores: RankingSubScores
    recommendation: Literal["Strong Match", "Good Match", "Possible Match", "Not a Match"]
    strengths: list[str]
    weaknesses: list[str]
    match_explanation: str
    scoring_rule_source: Literal["campaign_override", "organization_default", "system_default"]
    current_company: str | None
    years_of_experience: float | None
    review_status: ReviewStatus

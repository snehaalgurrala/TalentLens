from uuid import UUID

from pydantic import BaseModel


class ScoreDistributionBucket(BaseModel):
    label: str
    count: int


class CompletionTrendPoint(BaseModel):
    date: str
    completed_count: int


class PerformerEntry(BaseModel):
    session_id: UUID
    candidate_name: str
    campaign_title: str
    overall_score: float


class AssessmentAnalyticsResponse(BaseModel):
    total_sessions: int
    completed_sessions: int
    completion_rate: float
    average_communication_score: float | None
    average_read_aloud_score: float | None
    average_listen_repeat_score: float | None
    total_invitations_sent: int
    invitations_accepted: int
    invitation_acceptance_rate: float
    top_performers: list[PerformerEntry]
    lowest_performers: list[PerformerEntry]
    score_distribution: list[ScoreDistributionBucket]
    completion_trend: list[CompletionTrendPoint]

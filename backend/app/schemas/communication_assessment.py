from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.communication_assessment import CommunicationAssessmentStatus


class CommunicationAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_session_id: UUID
    status: CommunicationAssessmentStatus
    overall_score: float | None
    reading_score: float | None
    listening_score: float | None
    confidence_score: float | None
    strengths_json: list[str] | None
    improvements_json: list[str] | None
    summary_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

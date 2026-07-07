from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.assessment_analysis import AnalysisStatus, AnalysisType


class AssessmentAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transcript_id: UUID
    analysis_type: AnalysisType
    status: AnalysisStatus
    overall_score: float | None
    word_accuracy: float | None
    correct_words: int | None
    missing_words: int | None
    extra_words: int | None
    substituted_words: int | None
    total_words: int | None
    reading_speed_wpm: float | None
    completion_percentage: float | None
    semantic_similarity: float | None
    keyword_coverage: float | None
    analysis_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

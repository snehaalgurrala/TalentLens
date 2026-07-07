from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.assessment_transcript import TranscriptStatus


class AssessmentTranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recording_id: UUID
    status: TranscriptStatus
    transcript: str | None
    language: str | None
    model_name: str | None
    processing_time_ms: int | None
    segment_count: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment_recording import RecordingStatus, RecordingType
from app.models.assessment_session import AssessmentSection, AssessmentSessionStatus

# Fixed at 5 aptitude questions per section1 (matches the frontend's
# AssessmentRunnerProvider / SECTION1 mock data) — not configurable in this
# sprint since there is no AssessmentTemplate/AssessmentQuestion entity yet.
MIN_QUESTION_NUMBER = 1
MAX_QUESTION_NUMBER = 5

# Sanity ceiling on a *claimed* recording size before any bytes are actually
# uploaded (that endpoint lands in the next sprint) — mirrors the resume
# upload size guard so an obviously-bogus value is rejected up front.
MAX_RECORDING_SIZE_MB = 50


# ── AssessmentSession ─────────────────────────────────────────────────────────


class AssessmentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    campaign_id: UUID
    candidate_id: UUID
    current_section: AssessmentSection
    current_question: int | None
    status: AssessmentSessionStatus
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentSessionCreate(BaseModel):
    campaign_id: UUID
    candidate_id: UUID


class AssessmentSessionProgressUpdate(BaseModel):
    current_section: AssessmentSection | None = None
    current_question: int | None = Field(
        None, ge=MIN_QUESTION_NUMBER, le=MAX_QUESTION_NUMBER
    )


# ── AssessmentAnswer ───────────────────────────────────────────────────────────


class AssessmentAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    question_number: int
    answer: str
    created_at: datetime
    updated_at: datetime


class AssessmentAnswerCreate(BaseModel):
    question_number: int = Field(ge=MIN_QUESTION_NUMBER, le=MAX_QUESTION_NUMBER)
    answer: str = Field(min_length=1, max_length=5000)


# ── AssessmentRecording ────────────────────────────────────────────────────────


class AssessmentRecordingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    recording_type: RecordingType
    filename: str
    mime_type: str
    duration_seconds: float
    storage_path: str
    file_size: int
    status: RecordingStatus
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentRecordingCreate(BaseModel):
    recording_type: RecordingType
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=127)
    duration_seconds: float = Field(gt=0)
    file_size: int = Field(gt=0, le=MAX_RECORDING_SIZE_MB * 1024 * 1024)

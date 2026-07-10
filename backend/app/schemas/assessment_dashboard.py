from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.assessment_session import AssessmentSection, AssessmentSessionStatus
from app.models.communication_assessment import CommunicationAssessmentStatus
from app.models.resume_file import PipelineStage
from app.schemas.assessment_analysis import AssessmentAnalysisResponse
from app.schemas.assessment_session import AssessmentRecordingResponse, AssessmentSessionResponse
from app.schemas.assessment_transcript import AssessmentTranscriptResponse
from app.schemas.communication_assessment import CommunicationAssessmentResponse


class AssessmentRecordingDetail(BaseModel):
    recording: AssessmentRecordingResponse
    reference_sentence: str
    transcript: AssessmentTranscriptResponse | None
    analysis: AssessmentAnalysisResponse | None


class AssessmentSessionCandidateInfo(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str | None


class AssessmentSessionCampaignInfo(BaseModel):
    id: UUID
    title: str


class AssessmentSessionFullResponse(BaseModel):
    session: AssessmentSessionResponse
    candidate: AssessmentSessionCandidateInfo
    campaign: AssessmentSessionCampaignInfo
    # The candidate's current ATS pipeline stage (e.g. SHORTLISTED,
    # ASSESSMENT_SENT, ASSESSMENT_COMPLETED) — None only if no matching
    # ResumeFile row exists for this candidate+campaign (shouldn't happen in
    # practice since an assessment session implies one, but defensive).
    pipeline_stage: PipelineStage | None
    recordings: list[AssessmentRecordingDetail]
    communication_assessment: CommunicationAssessmentResponse | None


class AssessmentSessionListItem(BaseModel):
    session_id: UUID
    candidate: AssessmentSessionCandidateInfo
    campaign: AssessmentSessionCampaignInfo
    status: AssessmentSessionStatus
    current_section: AssessmentSection
    progress_percent: int
    started_at: datetime
    completed_at: datetime | None
    overall_score: float | None
    communication_status: CommunicationAssessmentStatus | None


class AssessmentSessionListResponse(BaseModel):
    items: list[AssessmentSessionListItem]
    total: int

from pydantic import BaseModel

from app.schemas.assessment_analysis import AssessmentAnalysisResponse
from app.schemas.assessment_session import AssessmentRecordingResponse, AssessmentSessionResponse
from app.schemas.assessment_transcript import AssessmentTranscriptResponse
from app.schemas.communication_assessment import CommunicationAssessmentResponse


class AssessmentRecordingDetail(BaseModel):
    recording: AssessmentRecordingResponse
    reference_sentence: str
    transcript: AssessmentTranscriptResponse | None
    analysis: AssessmentAnalysisResponse | None


class AssessmentSessionFullResponse(BaseModel):
    session: AssessmentSessionResponse
    recordings: list[AssessmentRecordingDetail]
    communication_assessment: CommunicationAssessmentResponse | None

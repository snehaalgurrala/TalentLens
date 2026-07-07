import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.assessment_transcript import AssessmentTranscriptRepository
from app.schemas.assessment_transcript import AssessmentTranscriptResponse
from app.services.assessment_transcript import AssessmentTranscriptService

router = APIRouter()

# Same access model as assessment_sessions.py: candidates have no platform
# account/token yet, so every call here is made on a candidate's behalf by an
# org member.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def get_assessment_transcript_service(db: DBSession) -> AssessmentTranscriptService:
    return AssessmentTranscriptService(AssessmentTranscriptRepository(db))


AssessmentTranscriptServiceDep = Annotated[
    AssessmentTranscriptService, Depends(get_assessment_transcript_service)
]


@router.get(
    "/{recording_id}",
    response_model=AssessmentTranscriptResponse,
    summary="Get the transcription status/result for a recording",
    responses={404: {"description": "Transcript not found."}},
)
async def get_assessment_transcript(
    recording_id: uuid.UUID,
    service: AssessmentTranscriptServiceDep,
    current_user: RecruiterUser,
) -> AssessmentTranscriptResponse:
    transcript = await service.get_transcript(recording_id, current_user)
    return AssessmentTranscriptResponse.model_validate(transcript)

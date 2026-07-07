import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.assessment_analysis import AssessmentAnalysisRepository
from app.schemas.assessment_analysis import AssessmentAnalysisResponse
from app.services.assessment_analysis import AssessmentAnalysisService

router = APIRouter()

# Same access model as assessment_transcripts.py: candidates have no platform
# account/token yet, so every call here is made on a candidate's behalf by an
# org member.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def get_assessment_analysis_service(db: DBSession) -> AssessmentAnalysisService:
    return AssessmentAnalysisService(AssessmentAnalysisRepository(db))


AssessmentAnalysisServiceDep = Annotated[
    AssessmentAnalysisService, Depends(get_assessment_analysis_service)
]


@router.get(
    "/{transcript_id}",
    response_model=AssessmentAnalysisResponse,
    summary="Get the Read Aloud communication analysis for a transcript",
    responses={404: {"description": "Analysis not found."}},
)
async def get_assessment_analysis(
    transcript_id: uuid.UUID,
    service: AssessmentAnalysisServiceDep,
    current_user: RecruiterUser,
) -> AssessmentAnalysisResponse:
    analysis = await service.get_analysis(transcript_id, current_user)
    return AssessmentAnalysisResponse.model_validate(analysis)

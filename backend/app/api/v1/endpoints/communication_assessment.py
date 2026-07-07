import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.communication_assessment import CommunicationAssessmentRepository
from app.schemas.communication_assessment import CommunicationAssessmentResponse
from app.services.communication_assessment import CommunicationAssessmentService

router = APIRouter()

# Same access model as assessment_analysis.py: candidates have no platform
# account/token yet, so every call here is made on a candidate's behalf by an
# org member.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def get_communication_assessment_service(db: DBSession) -> CommunicationAssessmentService:
    return CommunicationAssessmentService(CommunicationAssessmentRepository(db))


CommunicationAssessmentServiceDep = Annotated[
    CommunicationAssessmentService, Depends(get_communication_assessment_service)
]


@router.get(
    "/{session_id}",
    response_model=CommunicationAssessmentResponse,
    summary="Get the aggregate communication assessment for an assessment session",
    responses={404: {"description": "Communication assessment not found."}},
)
async def get_communication_assessment(
    session_id: uuid.UUID,
    service: CommunicationAssessmentServiceDep,
    current_user: RecruiterUser,
) -> CommunicationAssessmentResponse:
    assessment = await service.get_assessment(session_id, current_user)
    return CommunicationAssessmentResponse.model_validate(assessment)

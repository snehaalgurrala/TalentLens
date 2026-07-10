import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.assessment_invitation import AssessmentInvitationRepository
from app.repositories.assessment_session import AssessmentSessionRepository
from app.repositories.communication_assessment import CommunicationAssessmentRepository
from app.schemas.assessment_analytics import AssessmentAnalyticsResponse
from app.services.assessment_analytics import AssessmentAnalyticsService

router = APIRouter()

_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def get_assessment_analytics_service(db: DBSession) -> AssessmentAnalyticsService:
    return AssessmentAnalyticsService(
        session_repo=AssessmentSessionRepository(db),
        communication_assessment_repo=CommunicationAssessmentRepository(db),
        invitation_repo=AssessmentInvitationRepository(db),
    )


AssessmentAnalyticsServiceDep = Annotated[
    AssessmentAnalyticsService, Depends(get_assessment_analytics_service)
]


@router.get(
    "",
    response_model=AssessmentAnalyticsResponse,
    summary="Aggregate assessment analytics for the organization (optionally filtered by campaign)",
    responses={
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_assessment_analytics(
    service: AssessmentAnalyticsServiceDep,
    current_user: RecruiterUser,
    campaign_id: uuid.UUID | None = None,
) -> AssessmentAnalyticsResponse:
    return await service.get_summary(current_user, campaign_id)

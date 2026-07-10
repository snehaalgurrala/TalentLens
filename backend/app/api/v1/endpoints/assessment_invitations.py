from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.assessment_invitation import AssessmentInvitationRepository
from app.repositories.assessment_session import AssessmentSessionRepository
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.candidate_activity import CandidateActivityRepository
from app.repositories.resume_file import ResumeFileRepository
from app.schemas.assessment_invitation import (
    AssessmentInvitationDetailResponse,
    AssessmentInvitationSendRequest,
    AssessmentInvitationSendResult,
)
from app.services.assessment_invitation import AssessmentInvitationService
from app.services.email.email_service import EmailService
from app.services.email.smtp_provider import SMTPProvider

router = APIRouter()

_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def get_assessment_invitation_service(db: DBSession) -> AssessmentInvitationService:
    return AssessmentInvitationService(
        invitation_repo=AssessmentInvitationRepository(db),
        session_repo=AssessmentSessionRepository(db),
        campaign_repo=CampaignRepository(db),
        candidate_repo=CandidateRepository(db),
        email_service=EmailService(SMTPProvider()),
        resume_file_repo=ResumeFileRepository(db),
        activity_repo=CandidateActivityRepository(db),
    )


AssessmentInvitationServiceDep = Annotated[
    AssessmentInvitationService, Depends(get_assessment_invitation_service)
]


@router.post(
    "/send",
    response_model=AssessmentInvitationSendResult,
    status_code=status.HTTP_201_CREATED,
    summary="Invite one or more candidates to take a campaign's assessment",
    responses={
        201: {"description": "Per-candidate success/failure results."},
        404: {"description": "Campaign not found in your organization."},
    },
)
async def send_assessment_invitations(
    data: AssessmentInvitationSendRequest,
    service: AssessmentInvitationServiceDep,
    current_user: RecruiterUser,
) -> AssessmentInvitationSendResult:
    return await service.send_invitations(data, current_user)


@router.get(
    "/{token}",
    response_model=AssessmentInvitationDetailResponse,
    summary="Validate an invitation token and fetch its assessment details",
    responses={
        404: {"description": "Invitation not found."},
        410: {"description": "Invitation has expired, been revoked, or already been completed."},
    },
)
async def get_assessment_invitation(
    token: str,
    service: AssessmentInvitationServiceDep,
) -> AssessmentInvitationDetailResponse:
    """Public — secured only by the token's entropy, same access model as any
    emailed magic link. No RBAC dependency: candidates have no platform
    account in this sprint."""
    return await service.get_invitation_by_token(token)


@router.post(
    "/{token}/start",
    response_model=AssessmentInvitationDetailResponse,
    summary="Mark an invitation STARTED once the candidate begins the assessment",
    responses={
        404: {"description": "Invitation not found."},
        410: {"description": "Invitation has expired, been revoked, or already been completed."},
    },
)
async def start_assessment_invitation(
    token: str,
    service: AssessmentInvitationServiceDep,
) -> AssessmentInvitationDetailResponse:
    """Public, same access model as GET /{token}. Idempotent: calling this
    again on an already-STARTED invitation is a no-op."""
    return await service.mark_started(token)


@router.post(
    "/{token}/complete",
    response_model=AssessmentInvitationDetailResponse,
    summary="Mark an invitation COMPLETED once the candidate finishes the assessment",
    responses={
        404: {"description": "Invitation not found."},
        410: {"description": "Invitation has expired or been revoked."},
    },
)
async def complete_assessment_invitation(
    token: str,
    service: AssessmentInvitationServiceDep,
) -> AssessmentInvitationDetailResponse:
    """Public, same access model as GET /{token}. Idempotent: calling this
    again on an already-COMPLETED invitation is a no-op, not an error."""
    return await service.mark_completed(token)

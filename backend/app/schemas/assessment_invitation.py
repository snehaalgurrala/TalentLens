from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.assessment_invitation import AssessmentInvitationStatus
from app.models.assessment_session import AssessmentSessionStatus

# Bounds on how long a candidate has to act on an invitation before it must
# be resent — 1 hour to 90 days.
MIN_EXPIRATION_HOURS = 1
MAX_EXPIRATION_HOURS = 24 * 90


# ── Recruiter: send invitations ────────────────────────────────────────────


class AssessmentInvitationSendRequest(BaseModel):
    campaign_id: UUID
    candidate_ids: list[UUID] = Field(min_length=1, max_length=200)
    expiration_hours: int = Field(ge=MIN_EXPIRATION_HOURS, le=MAX_EXPIRATION_HOURS)


class AssessmentInvitationSendFailure(BaseModel):
    candidate_id: UUID
    reason: str


class AssessmentInvitationSendSuccess(BaseModel):
    candidate_id: UUID
    invitation_id: UUID


class AssessmentInvitationSendResult(BaseModel):
    succeeded: list[AssessmentInvitationSendSuccess]
    failed: list[AssessmentInvitationSendFailure]


# ── Candidate: validate token ──────────────────────────────────────────────


class AssessmentInvitationCampaignInfo(BaseModel):
    id: UUID
    title: str


class AssessmentInvitationSessionInfo(BaseModel):
    id: UUID
    status: AssessmentSessionStatus


class AssessmentInvitationDetailResponse(BaseModel):
    assessment_session: AssessmentInvitationSessionInfo
    campaign: AssessmentInvitationCampaignInfo
    candidate_display_name: str
    status: AssessmentInvitationStatus
    expires_at: datetime

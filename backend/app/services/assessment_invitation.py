"""AssessmentInvitationService — creates/resumes the AssessmentSession behind
a recruiter's "send invitation" action, generates a cryptographically random
access token (only its SHA-256 hash is ever persisted, same pattern as
OrganizationInvitation), and hands the rendered email off to an injected
EmailService. Never talks to SMTP directly — that lives behind
EmailProvider (see app/services/email/) so the transport can change without
touching this module.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import generate_invitation_token, hash_token
from app.models.assessment_invitation import AssessmentInvitation, AssessmentInvitationStatus
from app.models.assessment_session import AssessmentSection, AssessmentSessionStatus
from app.models.candidate_activity import ActivityEventType
from app.models.resume_file import PipelineStage
from app.schemas.assessment_invitation import (
    AssessmentInvitationCampaignInfo,
    AssessmentInvitationDetailResponse,
    AssessmentInvitationSendFailure,
    AssessmentInvitationSendRequest,
    AssessmentInvitationSendResult,
    AssessmentInvitationSendSuccess,
    AssessmentInvitationSessionInfo,
)
from app.services.pipeline_transitions import advance_pipeline_stage

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.user import User
    from app.repositories.assessment_invitation import AssessmentInvitationRepository
    from app.repositories.assessment_session import AssessmentSessionRepository
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.resume_file import ResumeFileRepository
    from app.services.email.email_service import EmailService

logger = logging.getLogger(__name__)

# First aptitude question a freshly created session lands on — mirrors
# AssessmentSessionService.create_or_resume.
_INITIAL_QUESTION_NUMBER = 1

# No AssessmentTemplate entity exists yet to report a real duration, so the
# email shows a fixed estimate (per-campaign durations are a future sprint).
_DEFAULT_DURATION_DISPLAY = "Approximately 20-30 minutes"

_TERMINAL_STATUSES = (
    AssessmentInvitationStatus.EXPIRED,
    AssessmentInvitationStatus.REVOKED,
    AssessmentInvitationStatus.COMPLETED,
)


class _SendFailureError(Exception):
    """Internal control-flow signal: stop processing one candidate and
    record `str(self)` as their failure reason, without aborting the rest of
    the batch."""


class AssessmentInvitationService:
    def __init__(
        self,
        invitation_repo: AssessmentInvitationRepository,
        session_repo: AssessmentSessionRepository,
        campaign_repo: CampaignRepository,
        candidate_repo: CandidateRepository,
        email_service: EmailService,
        resume_file_repo: ResumeFileRepository,
        activity_repo: CandidateActivityRepository,
    ) -> None:
        self.invitation_repo = invitation_repo
        self.session_repo = session_repo
        self.campaign_repo = campaign_repo
        self.candidate_repo = candidate_repo
        self.email_service = email_service
        self.resume_file_repo = resume_file_repo
        self.activity_repo = activity_repo

    # ── Internal guards ───────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage assessment invitations.",
            )
        return user.org_id

    def _build_assessment_url(self, token: str) -> str:
        return f"{settings.FRONTEND_BASE_URL}/assessment/start/{token}"

    # ── Recruiter: send invitations ───────────────────────────────────────────

    async def send_invitations(
        self, data: AssessmentInvitationSendRequest, user: User
    ) -> AssessmentInvitationSendResult:
        org_id = self._require_org(user)
        campaign = await self.campaign_repo.get_by_id(data.campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found."
            )

        succeeded: list[AssessmentInvitationSendSuccess] = []
        failed: list[AssessmentInvitationSendFailure] = []

        for candidate_id in data.candidate_ids:
            try:
                invitation = await self._send_one(
                    campaign, candidate_id, data.expiration_hours, org_id
                )
            except _SendFailureError as exc:
                failed.append(
                    AssessmentInvitationSendFailure(candidate_id=candidate_id, reason=str(exc))
                )
            else:
                succeeded.append(
                    AssessmentInvitationSendSuccess(
                        candidate_id=candidate_id, invitation_id=invitation.id
                    )
                )

        return AssessmentInvitationSendResult(succeeded=succeeded, failed=failed)

    async def _send_one(
        self,
        campaign: Campaign,
        candidate_id: uuid.UUID,
        expiration_hours: int,
        org_id: uuid.UUID,
    ) -> AssessmentInvitation:
        candidate = await self.candidate_repo.get_by_id_and_org(candidate_id, org_id)
        if candidate is None:
            raise _SendFailureError("Candidate not found in your organization.")
        if not candidate.email:
            raise _SendFailureError("Candidate has no email on file.")

        assessment_session = await self.session_repo.get_by_campaign_and_candidate(
            campaign.id, candidate.id, org_id
        )
        if assessment_session is None:
            assessment_session = await self.session_repo.create(
                org_id=org_id,
                campaign_id=campaign.id,
                candidate_id=candidate.id,
                current_section=AssessmentSection.APTITUDE,
                current_question=_INITIAL_QUESTION_NUMBER,
                status=AssessmentSessionStatus.IN_PROGRESS,
            )

        invitation = await self.invitation_repo.get_by_session(assessment_session.id)
        if invitation is not None and invitation.status == AssessmentInvitationStatus.COMPLETED:
            raise _SendFailureError("Candidate has already completed this assessment.")

        token = generate_invitation_token()
        expires_at = datetime.now(UTC) + timedelta(hours=expiration_hours)

        if invitation is None:
            invitation = await self.invitation_repo.create(
                organization_id=org_id,
                assessment_session_id=assessment_session.id,
                candidate_id=candidate.id,
                campaign_id=campaign.id,
                token_hash=hash_token(token),
                status=AssessmentInvitationStatus.PENDING,
                expires_at=expires_at,
            )
        else:
            # Resend: fresh token/expiry, restart the lifecycle timestamps.
            invitation = await self.invitation_repo.update(
                invitation,
                token_hash=hash_token(token),
                status=AssessmentInvitationStatus.PENDING,
                expires_at=expires_at,
                sent_at=None,
                opened_at=None,
                started_at=None,
            )

        try:
            await self.email_service.send_assessment_invitation(
                to_email=candidate.email,
                candidate_name=f"{candidate.first_name} {candidate.last_name}",
                campaign_name=campaign.title,
                assessment_url=self._build_assessment_url(token),
                expires_at_display=expires_at.strftime("%B %d, %Y at %H:%M UTC"),
                duration_display=_DEFAULT_DURATION_DISPLAY,
            )
        except Exception:
            logger.exception(
                "Failed to send assessment invitation email",
                extra={"candidate_id": str(candidate_id), "invitation_id": str(invitation.id)},
            )
            raise _SendFailureError("Failed to send invitation email.") from None

        invitation = await self.invitation_repo.mark_sent(invitation)
        # Only after the invitation is created AND the email genuinely sends
        # (never before) — see PART 2 of the automatic-pipeline-workflow
        # sprint doc.
        await advance_pipeline_stage(
            self.resume_file_repo,
            self.activity_repo,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            target_stage=PipelineStage.ASSESSMENT_SENT,
            event_type=ActivityEventType.ASSESSMENT_INVITATION_SENT,
        )
        return invitation

    # ── Candidate: validate token ─────────────────────────────────────────────

    async def _get_live_invitation(self, token: str) -> AssessmentInvitation:
        """Look up by token, lazily expiring a stale row, and reject the two
        statuses every candidate-facing endpoint treats the same way
        (REVOKED/EXPIRED). COMPLETED is deliberately left to each caller:
        GET treats it as terminal, but marking-complete is idempotent."""
        invitation = await self.invitation_repo.get_by_token_hash(hash_token(token))
        if invitation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found."
            )

        if invitation.expires_at < datetime.now(UTC) and invitation.status not in _TERMINAL_STATUSES:
            invitation = await self.invitation_repo.expire(invitation)

        if invitation.status == AssessmentInvitationStatus.REVOKED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="This invitation has been revoked."
            )
        if invitation.status == AssessmentInvitationStatus.EXPIRED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="This invitation has expired."
            )
        return invitation

    async def _build_detail_response(
        self, invitation: AssessmentInvitation
    ) -> AssessmentInvitationDetailResponse:
        assessment_session = await self.session_repo.get_by_id(
            invitation.assessment_session_id, invitation.organization_id
        )
        campaign = await self.campaign_repo.get_by_id(
            invitation.campaign_id, invitation.organization_id
        )
        candidate = await self.candidate_repo.get_by_id_and_org(
            invitation.candidate_id, invitation.organization_id
        )
        if assessment_session is None or campaign is None or candidate is None:
            # FKs cascade-delete together with the invitation, so reaching
            # here means unexpected data loss rather than a normal
            # candidate-facing condition.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found."
            )

        return AssessmentInvitationDetailResponse(
            assessment_session=AssessmentInvitationSessionInfo(
                id=assessment_session.id, status=assessment_session.status
            ),
            campaign=AssessmentInvitationCampaignInfo(id=campaign.id, title=campaign.title),
            candidate_display_name=f"{candidate.first_name} {candidate.last_name}",
            status=invitation.status,
            expires_at=invitation.expires_at,
        )

    async def get_invitation_by_token(self, token: str) -> AssessmentInvitationDetailResponse:
        invitation = await self._get_live_invitation(token)
        if invitation.status == AssessmentInvitationStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This assessment has already been completed.",
            )

        if invitation.status in (
            AssessmentInvitationStatus.PENDING,
            AssessmentInvitationStatus.SENT,
        ):
            invitation = await self.invitation_repo.mark_opened(invitation)
            # Opening the link starts the workflow — do not wait for
            # completion (see PART 2 of the automatic-pipeline-workflow
            # sprint doc).
            await advance_pipeline_stage(
                self.resume_file_repo,
                self.activity_repo,
                candidate_id=invitation.candidate_id,
                campaign_id=invitation.campaign_id,
                target_stage=PipelineStage.ASSESSMENT_IN_PROGRESS,
                event_type=ActivityEventType.ASSESSMENT_STARTED,
            )

        return await self._build_detail_response(invitation)

    async def mark_started(self, token: str) -> AssessmentInvitationDetailResponse:
        """Called once the candidate actually begins the assessment (past
        instructions, not just opening the emailed link — see mark_opened
        in get_invitation_by_token for that earlier transition)."""
        invitation = await self._get_live_invitation(token)
        if invitation.status == AssessmentInvitationStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This assessment has already been completed.",
            )
        if invitation.status != AssessmentInvitationStatus.STARTED:
            invitation = await self.invitation_repo.mark_started(invitation)

        return await self._build_detail_response(invitation)

    async def mark_completed(self, token: str) -> AssessmentInvitationDetailResponse:
        """Idempotent: an already-COMPLETED invitation is left as-is rather
        than rejected, since the candidate's own retry/double-submit should
        not surface as an error."""
        invitation = await self._get_live_invitation(token)
        if invitation.status != AssessmentInvitationStatus.COMPLETED:
            invitation = await self.invitation_repo.mark_completed(invitation)

        return await self._build_detail_response(invitation)

"""Unit tests for AssessmentInvitationService. All repositories and the
EmailService are mocked (AsyncMock) — no database, no SMTP."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.assessment_invitation import AssessmentInvitation, AssessmentInvitationStatus
from app.models.assessment_session import (
    AssessmentSection,
    AssessmentSession,
    AssessmentSessionStatus,
)
from app.models.campaign import Campaign
from app.models.candidate import Candidate
from app.models.candidate_activity import ActivityEventType
from app.models.resume_file import PipelineStage
from app.models.user import User, UserRole
from app.schemas.assessment_invitation import AssessmentInvitationSendRequest
from app.services.assessment_invitation import AssessmentInvitationService

_ORG_ID = uuid.uuid4()


def make_user(org_id: uuid.UUID | None = _ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="recruiter@example.com",
        full_name="Recruiter",
        password_hash="$2b$12$irrelevant",
        role=UserRole.RECRUITER,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_campaign(**overrides) -> Campaign:
    defaults = dict(
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        title="Backend Engineer",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    campaign = Campaign()
    for k, v in defaults.items():
        setattr(campaign, k, v)
    return campaign


def make_candidate(**overrides) -> Candidate:
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    candidate = Candidate()
    for k, v in defaults.items():
        setattr(candidate, k, v)
    return candidate


def make_session(**overrides) -> AssessmentSession:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        campaign_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        current_section=AssessmentSection.APTITUDE,
        current_question=1,
        status=AssessmentSessionStatus.IN_PROGRESS,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentSession(**defaults)


def make_invitation(**overrides) -> AssessmentInvitation:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        token_hash="existing-hash",
        status=AssessmentInvitationStatus.PENDING,
        expires_at=now + timedelta(hours=48),
        sent_at=None,
        opened_at=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentInvitation(**defaults)


def make_resume_file(**overrides) -> MagicMock:
    defaults = dict(id=uuid.uuid4(), pipeline_stage=PipelineStage.SHORTLISTED)
    defaults.update(overrides)
    resume_file = MagicMock()
    resume_file.id = defaults["id"]
    resume_file.pipeline_stage = defaults["pipeline_stage"]
    return resume_file


def _default_resume_file_repo() -> MagicMock:
    # No matching ResumeFile row by default — advance_pipeline_stage becomes
    # a safe no-op so tests that don't care about the pipeline-stage nudge
    # don't need to stub it out themselves.
    repo = MagicMock()
    repo.get_by_candidate_and_campaign = AsyncMock(return_value=None)
    return repo


def make_service(
    invitation_repo=None,
    session_repo=None,
    campaign_repo=None,
    candidate_repo=None,
    email_service=None,
    resume_file_repo=None,
    activity_repo=None,
) -> AssessmentInvitationService:
    return AssessmentInvitationService(
        invitation_repo=invitation_repo or MagicMock(),
        session_repo=session_repo or MagicMock(),
        campaign_repo=campaign_repo or MagicMock(),
        candidate_repo=candidate_repo or MagicMock(),
        email_service=email_service or MagicMock(),
        resume_file_repo=resume_file_repo or _default_resume_file_repo(),
        activity_repo=activity_repo or MagicMock(),
    )


# ── send_invitations ────────────────────────────────────────────────────────


class TestSendInvitations:
    async def test_campaign_not_found_raises_404(self):
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(campaign_repo=campaign_repo)
        data = AssessmentInvitationSendRequest(
            campaign_id=uuid.uuid4(), candidate_ids=[uuid.uuid4()], expiration_hours=48
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.send_invitations(data, make_user())

        assert exc_info.value.status_code == 404

    async def test_new_candidate_creates_session_and_invitation_and_sends_email(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        created_invitation = make_invitation(
            assessment_session_id=session_row.id, candidate_id=candidate.id, campaign_id=campaign.id
        )

        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=None)
        session_repo.create = AsyncMock(return_value=session_row)
        invitation_repo = MagicMock()
        invitation_repo.get_by_session = AsyncMock(return_value=None)
        invitation_repo.create = AsyncMock(return_value=created_invitation)
        invitation_repo.mark_sent = AsyncMock(
            return_value=make_invitation(
                id=created_invitation.id, status=AssessmentInvitationStatus.SENT
            )
        )
        email_service = MagicMock()
        email_service.send_assessment_invitation = AsyncMock()

        service = make_service(
            invitation_repo=invitation_repo,
            session_repo=session_repo,
            campaign_repo=campaign_repo,
            candidate_repo=candidate_repo,
            email_service=email_service,
        )
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=48
        )

        result = await service.send_invitations(data, make_user())

        assert len(result.succeeded) == 1
        assert result.succeeded[0].candidate_id == candidate.id
        assert result.failed == []
        session_repo.create.assert_awaited_once()
        invitation_repo.create.assert_awaited_once()
        email_service.send_assessment_invitation.assert_awaited_once()
        invitation_repo.mark_sent.assert_awaited_once()

    async def test_successful_send_advances_pipeline_stage_to_assessment_sent(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        created_invitation = make_invitation(
            assessment_session_id=session_row.id, candidate_id=candidate.id, campaign_id=campaign.id
        )
        resume_file = make_resume_file(pipeline_stage=PipelineStage.SHORTLISTED)

        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=None)
        session_repo.create = AsyncMock(return_value=session_row)
        invitation_repo = MagicMock()
        invitation_repo.get_by_session = AsyncMock(return_value=None)
        invitation_repo.create = AsyncMock(return_value=created_invitation)
        invitation_repo.mark_sent = AsyncMock(
            return_value=make_invitation(
                id=created_invitation.id, status=AssessmentInvitationStatus.SENT
            )
        )
        email_service = MagicMock()
        email_service.send_assessment_invitation = AsyncMock()
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock(return_value=resume_file)
        resume_file_repo.update = AsyncMock(return_value=resume_file)
        activity_repo = MagicMock()
        activity_repo.create = AsyncMock()

        service = make_service(
            invitation_repo=invitation_repo,
            session_repo=session_repo,
            campaign_repo=campaign_repo,
            candidate_repo=candidate_repo,
            email_service=email_service,
            resume_file_repo=resume_file_repo,
            activity_repo=activity_repo,
        )
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=48
        )

        result = await service.send_invitations(data, make_user())

        assert len(result.succeeded) == 1
        resume_file_repo.get_by_candidate_and_campaign.assert_awaited_once_with(
            candidate.id, campaign.id
        )
        resume_file_repo.update.assert_awaited_once_with(
            resume_file, pipeline_stage=PipelineStage.ASSESSMENT_SENT
        )
        activity_repo.create.assert_awaited_once_with(
            resume_file.id, None, ActivityEventType.ASSESSMENT_INVITATION_SENT
        )

    async def test_email_failure_does_not_advance_pipeline_stage(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        created_invitation = make_invitation(assessment_session_id=session_row.id)

        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=session_row)
        invitation_repo = MagicMock()
        invitation_repo.get_by_session = AsyncMock(return_value=None)
        invitation_repo.create = AsyncMock(return_value=created_invitation)
        invitation_repo.mark_sent = AsyncMock()
        email_service = MagicMock()
        email_service.send_assessment_invitation = AsyncMock(side_effect=RuntimeError("SMTP down"))
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock()

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
            email_service=email_service, resume_file_repo=resume_file_repo,
        )
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=24
        )

        await service.send_invitations(data, make_user())

        resume_file_repo.get_by_candidate_and_campaign.assert_not_called()

    async def test_resend_reuses_session_and_updates_existing_invitation(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        existing_invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.SENT,
        )

        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=session_row)
        invitation_repo = MagicMock()
        invitation_repo.get_by_session = AsyncMock(return_value=existing_invitation)
        invitation_repo.update = AsyncMock(return_value=existing_invitation)
        invitation_repo.mark_sent = AsyncMock(return_value=existing_invitation)
        email_service = MagicMock()
        email_service.send_assessment_invitation = AsyncMock()

        service = make_service(
            invitation_repo=invitation_repo,
            session_repo=session_repo,
            campaign_repo=campaign_repo,
            candidate_repo=candidate_repo,
            email_service=email_service,
        )
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=24
        )

        result = await service.send_invitations(data, make_user())

        assert len(result.succeeded) == 1
        session_repo.create.assert_not_called()
        invitation_repo.create.assert_not_called()
        invitation_repo.update.assert_awaited_once()

    async def test_candidate_not_found_is_a_failure_not_an_exception(self):
        campaign = make_campaign()
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=None)

        service = make_service(campaign_repo=campaign_repo, candidate_repo=candidate_repo)
        missing_id = uuid.uuid4()
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[missing_id], expiration_hours=24
        )

        result = await service.send_invitations(data, make_user())

        assert result.succeeded == []
        assert len(result.failed) == 1
        assert result.failed[0].candidate_id == missing_id
        assert "not found" in result.failed[0].reason.lower()

    async def test_candidate_without_email_is_a_failure(self):
        campaign = make_campaign()
        candidate = make_candidate(email=None)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(campaign_repo=campaign_repo, candidate_repo=candidate_repo)
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=24
        )

        result = await service.send_invitations(data, make_user())

        assert result.succeeded == []
        assert "no email" in result.failed[0].reason.lower()

    async def test_already_completed_invitation_is_a_failure(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        completed_invitation = make_invitation(
            assessment_session_id=session_row.id,
            status=AssessmentInvitationStatus.COMPLETED,
        )

        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=session_row)
        invitation_repo = MagicMock()
        invitation_repo.get_by_session = AsyncMock(return_value=completed_invitation)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=24
        )

        result = await service.send_invitations(data, make_user())

        assert result.succeeded == []
        assert "already completed" in result.failed[0].reason.lower()

    async def test_email_send_failure_is_a_failure_not_marked_sent(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        created_invitation = make_invitation(assessment_session_id=session_row.id)

        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=session_row)
        invitation_repo = MagicMock()
        invitation_repo.get_by_session = AsyncMock(return_value=None)
        invitation_repo.create = AsyncMock(return_value=created_invitation)
        invitation_repo.mark_sent = AsyncMock()
        email_service = MagicMock()
        email_service.send_assessment_invitation = AsyncMock(side_effect=RuntimeError("SMTP down"))

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
            email_service=email_service,
        )
        data = AssessmentInvitationSendRequest(
            campaign_id=campaign.id, candidate_ids=[candidate.id], expiration_hours=24
        )

        result = await service.send_invitations(data, make_user())

        assert result.succeeded == []
        assert "failed to send" in result.failed[0].reason.lower()
        invitation_repo.mark_sent.assert_not_called()


# ── get_invitation_by_token ──────────────────────────────────────────────────


class TestGetInvitationByToken:
    async def test_not_found_raises_404(self):
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=None)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_invitation_by_token("bogus-token")

        assert exc_info.value.status_code == 404

    async def test_revoked_raises_410(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.REVOKED)
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_invitation_by_token("token")

        assert exc_info.value.status_code == 410

    async def test_completed_raises_410(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.COMPLETED)
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_invitation_by_token("token")

        assert exc_info.value.status_code == 410

    async def test_past_expiry_auto_expires_and_raises_410(self):
        invitation = make_invitation(
            status=AssessmentInvitationStatus.SENT,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.expire = AsyncMock(
            return_value=make_invitation(
                id=invitation.id,
                status=AssessmentInvitationStatus.EXPIRED,
                expires_at=invitation.expires_at,
            )
        )
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_invitation_by_token("token")

        assert exc_info.value.status_code == 410
        invitation_repo.expire.assert_awaited_once()

    async def test_valid_pending_invitation_marks_opened_and_returns_detail(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.PENDING,
        )
        opened_invitation = make_invitation(
            id=invitation.id,
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.OPENED,
            expires_at=invitation.expires_at,
        )

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_opened = AsyncMock(return_value=opened_invitation)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )

        result = await service.get_invitation_by_token("token")

        invitation_repo.mark_opened.assert_awaited_once()
        assert result.status == AssessmentInvitationStatus.OPENED
        assert result.campaign.title == campaign.title
        assert result.candidate_display_name == "Jane Doe"
        assert result.assessment_session.id == session_row.id

    async def test_opening_link_advances_pipeline_stage_to_assessment_in_progress(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.SENT,
        )
        opened_invitation = make_invitation(
            id=invitation.id,
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.OPENED,
            expires_at=invitation.expires_at,
        )
        resume_file = make_resume_file(pipeline_stage=PipelineStage.ASSESSMENT_SENT)

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_opened = AsyncMock(return_value=opened_invitation)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)
        resume_file_repo = MagicMock()
        resume_file_repo.get_by_candidate_and_campaign = AsyncMock(return_value=resume_file)
        resume_file_repo.update = AsyncMock(return_value=resume_file)
        activity_repo = MagicMock()
        activity_repo.create = AsyncMock()

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
            resume_file_repo=resume_file_repo, activity_repo=activity_repo,
        )

        await service.get_invitation_by_token("token")

        resume_file_repo.get_by_candidate_and_campaign.assert_awaited_once_with(
            candidate.id, campaign.id
        )
        resume_file_repo.update.assert_awaited_once_with(
            resume_file, pipeline_stage=PipelineStage.ASSESSMENT_IN_PROGRESS
        )
        activity_repo.create.assert_awaited_once_with(
            resume_file.id, None, ActivityEventType.ASSESSMENT_STARTED
        )

    async def test_already_started_invitation_is_not_marked_opened_again(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.STARTED,
        )

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_opened = AsyncMock()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )

        result = await service.get_invitation_by_token("token")

        invitation_repo.mark_opened.assert_not_called()
        assert result.status == AssessmentInvitationStatus.STARTED


# ── mark_started ─────────────────────────────────────────────────────────────


class TestMarkStarted:
    async def test_not_found_raises_404(self):
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=None)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_started("bogus-token")

        assert exc_info.value.status_code == 404

    async def test_completed_raises_410(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.COMPLETED)
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_started("token")

        assert exc_info.value.status_code == 410

    async def test_revoked_raises_410(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.REVOKED)
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_started("token")

        assert exc_info.value.status_code == 410

    async def test_opened_invitation_is_marked_started(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.OPENED,
        )
        started_invitation = make_invitation(
            id=invitation.id,
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.STARTED,
            expires_at=invitation.expires_at,
        )

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_started = AsyncMock(return_value=started_invitation)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )

        result = await service.mark_started("token")

        invitation_repo.mark_started.assert_awaited_once()
        assert result.status == AssessmentInvitationStatus.STARTED

    async def test_already_started_is_idempotent(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.STARTED,
        )

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_started = AsyncMock()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )

        result = await service.mark_started("token")

        invitation_repo.mark_started.assert_not_called()
        assert result.status == AssessmentInvitationStatus.STARTED


# ── mark_completed ───────────────────────────────────────────────────────────


class TestMarkCompleted:
    async def test_not_found_raises_404(self):
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=None)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_completed("bogus-token")

        assert exc_info.value.status_code == 404

    async def test_revoked_raises_410(self):
        invitation = make_invitation(status=AssessmentInvitationStatus.REVOKED)
        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        service = make_service(invitation_repo=invitation_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.mark_completed("token")

        assert exc_info.value.status_code == 410

    async def test_started_invitation_is_marked_completed(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.STARTED,
        )
        completed_invitation = make_invitation(
            id=invitation.id,
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.COMPLETED,
            expires_at=invitation.expires_at,
        )

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_completed = AsyncMock(return_value=completed_invitation)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )

        result = await service.mark_completed("token")

        invitation_repo.mark_completed.assert_awaited_once()
        assert result.status == AssessmentInvitationStatus.COMPLETED

    async def test_already_completed_is_idempotent_not_an_error(self):
        campaign = make_campaign()
        candidate = make_candidate()
        session_row = make_session(campaign_id=campaign.id, candidate_id=candidate.id)
        invitation = make_invitation(
            assessment_session_id=session_row.id,
            candidate_id=candidate.id,
            campaign_id=campaign.id,
            status=AssessmentInvitationStatus.COMPLETED,
        )

        invitation_repo = MagicMock()
        invitation_repo.get_by_token_hash = AsyncMock(return_value=invitation)
        invitation_repo.mark_completed = AsyncMock()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=session_row)
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=campaign)
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=candidate)

        service = make_service(
            invitation_repo=invitation_repo, session_repo=session_repo,
            campaign_repo=campaign_repo, candidate_repo=candidate_repo,
        )

        result = await service.mark_completed("token")

        invitation_repo.mark_completed.assert_not_called()
        assert result.status == AssessmentInvitationStatus.COMPLETED

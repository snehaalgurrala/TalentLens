"""Direct unit tests for AssessmentAnalyticsService, using mocked repositories
— mirrors test_assessment_dashboard_service.py.
"""
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
from app.models.communication_assessment import (
    CommunicationAssessment,
    CommunicationAssessmentStatus,
)
from app.models.user import User, UserRole
from app.services.assessment_analytics import AssessmentAnalyticsService

_ORG_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.RECRUITER, org_id: uuid.UUID | None = _ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        password_hash="$2b$12$irrelevant",
        role=role,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_campaign(**overrides) -> MagicMock:
    defaults = dict(id=uuid.uuid4(), title="Frontend Engineer")
    defaults.update(overrides)
    campaign = MagicMock()
    campaign.id = defaults["id"]
    campaign.title = defaults["title"]
    return campaign


def make_candidate(**overrides) -> MagicMock:
    defaults = dict(id=uuid.uuid4(), first_name="Jane", last_name="Doe", email="jane@example.com")
    defaults.update(overrides)
    candidate = MagicMock()
    candidate.id = defaults["id"]
    candidate.first_name = defaults["first_name"]
    candidate.last_name = defaults["last_name"]
    candidate.email = defaults["email"]
    return candidate


def make_session(candidate=None, campaign=None, **overrides) -> AssessmentSession:
    now = datetime.now(UTC)
    candidate = candidate or make_candidate()
    campaign = campaign or make_campaign()
    defaults = dict(
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        campaign_id=campaign.id,
        candidate_id=candidate.id,
        current_section=AssessmentSection.APTITUDE,
        current_question=1,
        status=AssessmentSessionStatus.IN_PROGRESS,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    session_row = AssessmentSession(**defaults)
    session_row.candidate = candidate
    session_row.campaign = campaign
    return session_row


def make_communication_assessment(**overrides) -> CommunicationAssessment:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        status=CommunicationAssessmentStatus.COMPLETED,
        overall_score=85.0,
        reading_score=90.0,
        listening_score=80.0,
        confidence_score=88.0,
        strengths_json=None,
        improvements_json=None,
        summary_json=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return CommunicationAssessment(**defaults)


def make_invitation(**overrides) -> AssessmentInvitation:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        token_hash="hash",
        status=AssessmentInvitationStatus.SENT,
        expires_at=now + timedelta(hours=48),
        sent_at=now,
        opened_at=None,
        started_at=None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentInvitation(**defaults)


def make_service(**repo_overrides) -> AssessmentAnalyticsService:
    defaults = dict(
        session_repo=MagicMock(),
        communication_assessment_repo=MagicMock(),
        invitation_repo=MagicMock(),
    )
    defaults.update(repo_overrides)
    return AssessmentAnalyticsService(**defaults)


class TestGetSummary:
    async def test_requires_org(self):
        service = make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_summary(make_user(org_id=None))
        assert exc_info.value.status_code == 422

    async def test_empty_org_returns_zeros(self):
        session_repo = MagicMock()
        session_repo.list_by_org = AsyncMock(return_value=[])
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.list_by_session_ids = AsyncMock(return_value=[])
        invitation_repo = MagicMock()
        invitation_repo.list_by_org = AsyncMock(return_value=[])
        service = make_service(
            session_repo=session_repo,
            communication_assessment_repo=communication_assessment_repo,
            invitation_repo=invitation_repo,
        )

        result = await service.get_summary(make_user())

        assert result.total_sessions == 0
        assert result.completed_sessions == 0
        assert result.completion_rate == 0.0
        assert result.average_communication_score is None
        assert result.invitation_acceptance_rate == 0.0
        assert result.top_performers == []
        assert result.lowest_performers == []
        assert len(result.completion_trend) == 14

    async def test_completion_rate_and_averages(self):
        completed = make_session(status=AssessmentSessionStatus.COMPLETED, completed_at=datetime.now(UTC))
        in_progress = make_session(status=AssessmentSessionStatus.IN_PROGRESS)
        comm = make_communication_assessment(
            assessment_session_id=completed.id, overall_score=90.0, reading_score=92.0, listening_score=88.0
        )
        session_repo = MagicMock()
        session_repo.list_by_org = AsyncMock(return_value=[completed, in_progress])
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.list_by_session_ids = AsyncMock(return_value=[comm])
        invitation_repo = MagicMock()
        invitation_repo.list_by_org = AsyncMock(return_value=[])
        service = make_service(
            session_repo=session_repo,
            communication_assessment_repo=communication_assessment_repo,
            invitation_repo=invitation_repo,
        )

        result = await service.get_summary(make_user())

        assert result.total_sessions == 2
        assert result.completed_sessions == 1
        assert result.completion_rate == 50.0
        assert result.average_communication_score == 90.0
        assert result.average_read_aloud_score == 92.0
        assert result.average_listen_repeat_score == 88.0

    async def test_invitation_acceptance_rate(self):
        session_repo = MagicMock()
        session_repo.list_by_org = AsyncMock(return_value=[])
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.list_by_session_ids = AsyncMock(return_value=[])
        invitation_repo = MagicMock()
        invitation_repo.list_by_org = AsyncMock(
            return_value=[
                make_invitation(status=AssessmentInvitationStatus.PENDING),
                make_invitation(status=AssessmentInvitationStatus.SENT),
                make_invitation(status=AssessmentInvitationStatus.OPENED),
                make_invitation(status=AssessmentInvitationStatus.STARTED),
                make_invitation(status=AssessmentInvitationStatus.COMPLETED),
            ]
        )
        service = make_service(
            session_repo=session_repo,
            communication_assessment_repo=communication_assessment_repo,
            invitation_repo=invitation_repo,
        )

        result = await service.get_summary(make_user())

        # 4 sent-or-further (excludes PENDING), 3 of those accepted (OPENED/STARTED/COMPLETED)
        assert result.total_invitations_sent == 4
        assert result.invitations_accepted == 3
        assert result.invitation_acceptance_rate == 75.0

    async def test_top_and_lowest_performers_and_score_distribution(self):
        sessions = []
        comms = []
        for score in [95.0, 40.0, 70.0]:
            s = make_session(status=AssessmentSessionStatus.COMPLETED)
            c = make_communication_assessment(assessment_session_id=s.id, overall_score=score)
            sessions.append(s)
            comms.append(c)

        session_repo = MagicMock()
        session_repo.list_by_org = AsyncMock(return_value=sessions)
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.list_by_session_ids = AsyncMock(return_value=comms)
        invitation_repo = MagicMock()
        invitation_repo.list_by_org = AsyncMock(return_value=[])
        service = make_service(
            session_repo=session_repo,
            communication_assessment_repo=communication_assessment_repo,
            invitation_repo=invitation_repo,
        )

        result = await service.get_summary(make_user())

        assert [p.overall_score for p in result.top_performers] == [95.0, 70.0, 40.0]
        assert [p.overall_score for p in result.lowest_performers] == [40.0, 70.0, 95.0]
        buckets = {b.label: b.count for b in result.score_distribution}
        assert buckets["81-100"] == 1
        assert buckets["61-80"] == 1
        assert buckets["21-40"] == 1
        assert buckets["0-20"] == 0

    async def test_campaign_filter_passed_to_session_repo_and_invitations(self):
        campaign_id = uuid.uuid4()
        other_campaign_invitation = make_invitation(campaign_id=uuid.uuid4())
        matching_invitation = make_invitation(campaign_id=campaign_id)
        session_repo = MagicMock()
        session_repo.list_by_org = AsyncMock(return_value=[])
        communication_assessment_repo = MagicMock()
        communication_assessment_repo.list_by_session_ids = AsyncMock(return_value=[])
        invitation_repo = MagicMock()
        invitation_repo.list_by_org = AsyncMock(
            return_value=[other_campaign_invitation, matching_invitation]
        )
        service = make_service(
            session_repo=session_repo,
            communication_assessment_repo=communication_assessment_repo,
            invitation_repo=invitation_repo,
        )

        result = await service.get_summary(make_user(), campaign_id=campaign_id)

        session_repo.list_by_org.assert_called_once_with(_ORG_ID, campaign_id)
        assert result.total_invitations_sent == 1

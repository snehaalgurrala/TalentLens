"""Unit tests for GET /assessment/analytics — mirrors test_assessment_dashboard_api.py:
AssessmentAnalyticsService is mocked via dependency override; RBAC is exercised
against the CANDIDATE role.
"""
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

from app.api.deps import get_current_user
from app.api.v1.endpoints.assessment_analytics import get_assessment_analytics_service
from app.main import app
from app.models.user import User, UserRole
from app.schemas.assessment_analytics import AssessmentAnalyticsResponse

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


def make_analytics_response() -> AssessmentAnalyticsResponse:
    return AssessmentAnalyticsResponse(
        total_sessions=10,
        completed_sessions=6,
        completion_rate=60.0,
        average_communication_score=82.5,
        average_read_aloud_score=85.0,
        average_listen_repeat_score=80.0,
        total_invitations_sent=12,
        invitations_accepted=9,
        invitation_acceptance_rate=75.0,
        top_performers=[],
        lowest_performers=[],
        score_distribution=[],
        completion_trend=[],
    )


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_assessment_analytics_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_assessment_analytics_service, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate_role():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestGetAssessmentAnalytics:
    _url = "/api/v1/assessment/analytics"

    async def test_returns_summary(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.get_summary = AsyncMock(return_value=make_analytics_response())

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert body["total_sessions"] == 10
        assert body["completion_rate"] == 60.0
        assert body["invitation_acceptance_rate"] == 75.0

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 403
        mock_service.get_summary.assert_not_called()

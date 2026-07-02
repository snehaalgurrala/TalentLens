"""
Unit tests for the dashboard endpoints.

Strategy (mirrors tests/test_campaigns.py and tests/test_rankings.py):
  - get_dashboard_service is overridden with a MagicMock — no database required.
  - get_current_user is overridden per-test to simulate different roles.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.dashboard import get_dashboard_service
from app.main import app
from app.models.campaign import CampaignStatus
from app.models.resume_file import ReviewStatus
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    ActivityItemResponse,
    DashboardSummaryResponse,
    ProcessingStatusResponse,
    RecentCampaignResponse,
    TopCandidateResponse,
)

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


@pytest.fixture
def mock_dashboard_service():
    svc = MagicMock()
    app.dependency_overrides[get_dashboard_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_dashboard_service, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def org_admin():
    user = make_user(role=UserRole.ORG_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestDashboardSummary:
    _url = "/api/v1/dashboard/summary"

    async def test_recruiter_can_view_summary(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        summary = DashboardSummaryResponse(
            total_campaigns=5,
            active_campaigns=3,
            closed_campaigns=2,
            total_candidates=42,
            processing_candidates=4,
            shortlisted_candidates=6,
            rejected_candidates=1,
            average_match_score=78.5,
        )
        mock_dashboard_service.get_summary = AsyncMock(return_value=summary)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert body["total_campaigns"] == 5
        assert body["active_campaigns"] == 3
        assert body["average_match_score"] == 78.5

    async def test_summary_allows_null_average_match_score(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        summary = DashboardSummaryResponse(
            total_campaigns=0,
            active_campaigns=0,
            closed_campaigns=0,
            total_candidates=0,
            processing_candidates=0,
            shortlisted_candidates=0,
            rejected_candidates=0,
            average_match_score=None,
        )
        mock_dashboard_service.get_summary = AsyncMock(return_value=summary)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        assert res.json()["average_match_score"] is None

    async def test_org_admin_can_view_summary(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, org_admin: User
    ):
        mock_dashboard_service.get_summary = AsyncMock(
            return_value=DashboardSummaryResponse(
                total_campaigns=0,
                active_campaigns=0,
                closed_campaigns=0,
                total_candidates=0,
                processing_candidates=0,
                shortlisted_candidates=0,
                rejected_candidates=0,
                average_match_score=None,
            )
        )
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200

    async def test_candidate_cannot_view_summary(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 403

    async def test_unauthenticated_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 401


class TestRecentCampaigns:
    _url = "/api/v1/dashboard/recent-campaigns"

    async def test_returns_campaigns_ordered_most_recent_first(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        campaigns = [
            RecentCampaignResponse(
                id=uuid.uuid4(),
                title="Senior Backend Engineer",
                status=CampaignStatus.ACTIVE,
                created_at=datetime.now(UTC),
                candidate_count=12,
            ),
            RecentCampaignResponse(
                id=uuid.uuid4(),
                title="Product Designer",
                status=CampaignStatus.DRAFT,
                created_at=datetime.now(UTC),
                candidate_count=0,
            ),
        ]
        mock_dashboard_service.get_recent_campaigns = AsyncMock(return_value=campaigns)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2
        assert body[0]["title"] == "Senior Backend Engineer"
        assert body[0]["candidate_count"] == 12

    async def test_empty_org_returns_empty_list(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        mock_dashboard_service.get_recent_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json() == []

    async def test_limit_query_param_is_forwarded(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        mock_dashboard_service.get_recent_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url, params={"limit": 3})
        assert res.status_code == 200
        _, kwargs = mock_dashboard_service.get_recent_campaigns.call_args
        assert kwargs["limit"] == 3

    async def test_candidate_cannot_view(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 403


class TestTopCandidates:
    _url = "/api/v1/dashboard/top-candidates"

    async def test_returns_ranked_candidates(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        candidates = [
            TopCandidateResponse(
                candidate_id=uuid.uuid4(),
                candidate_name="Jane Doe",
                resume_file_id=uuid.uuid4(),
                match_score=92.0,
                campaign_id=uuid.uuid4(),
                campaign_name="Senior Backend Engineer",
                years_of_experience=6.0,
                current_company="Acme",
                review_status=ReviewStatus.PENDING,
            )
        ]
        mock_dashboard_service.get_top_candidates = AsyncMock(return_value=candidates)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert body[0]["candidate_name"] == "Jane Doe"
        assert body[0]["match_score"] == 92.0
        assert body[0]["review_status"] == "PENDING"

    async def test_no_active_campaigns_returns_empty_list(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        mock_dashboard_service.get_top_candidates = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json() == []

    async def test_candidate_cannot_view(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 403


class TestProcessingStatus:
    _url = "/api/v1/dashboard/processing-status"

    async def test_returns_queue_counters(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        status_response = ProcessingStatusResponse(
            parsing_queue=2,
            embedding_queue=1,
            ranking_queue=5,
            failed_jobs=0,
            completed_jobs=10,
        )
        mock_dashboard_service.get_processing_status = AsyncMock(return_value=status_response)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert body["parsing_queue"] == 2
        assert body["completed_jobs"] == 10

    async def test_candidate_cannot_view(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 403


class TestActivityFeed:
    _url = "/api/v1/dashboard/activity"

    async def test_returns_events_newest_first(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        events = [
            ActivityItemResponse(
                id="campaign-created:1",
                type="CAMPAIGN_CREATED",
                description='Campaign "Senior Backend Engineer" was created.',
                occurred_at=datetime.now(UTC),
                campaign_id=uuid.uuid4(),
                campaign_name="Senior Backend Engineer",
            ),
            ActivityItemResponse(
                id="resume-uploaded:1",
                type="RESUME_UPLOADED",
                description='Resume "alice.pdf" was uploaded to "Senior Backend Engineer".',
                occurred_at=datetime.now(UTC),
                campaign_id=uuid.uuid4(),
                campaign_name="Senior Backend Engineer",
            ),
        ]
        mock_dashboard_service.get_activity = AsyncMock(return_value=events)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2
        assert body[0]["type"] == "CAMPAIGN_CREATED"

    async def test_empty_org_returns_empty_list(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, recruiter: User
    ):
        mock_dashboard_service.get_activity = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json() == []

    async def test_candidate_cannot_view(
        self, client_no_lifespan: AsyncClient, mock_dashboard_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 403

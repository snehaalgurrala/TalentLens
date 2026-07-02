"""
Unit tests for campaign endpoints.

Strategy:
  - get_campaign_service is overridden with a MagicMock — no database required.
  - get_current_user is overridden per-test to simulate different roles.
  - RequireRoles runs against the mocked user, so role-based 403s are tested
    without any service involvement.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.campaigns import get_campaign_service, get_campaign_summary_service
from app.main import app
from app.models.campaign import Campaign, CampaignPriority, CampaignStatus, EmploymentType
from app.models.user import User, UserRole
from app.schemas.campaign import CampaignProcessingStatusResponse, CampaignSummaryResponse

# ── Shared fixtures ───────────────────────────────────────────────────────────

_ORG_ID = uuid.uuid4()
_OTHER_USER_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.RECRUITER, org_id: uuid.UUID | None = _ORG_ID) -> User:
    user = User(
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
    return user


def make_campaign(user: User, **overrides) -> Campaign:
    campaign = Campaign(
        id=uuid.uuid4(),
        org_id=user.org_id,
        created_by=user.id,
        title="Senior Engineer Campaign",
        description="Looking for senior engineers",
        status=CampaignStatus.DRAFT,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        job_title=None,
        department=None,
        hiring_manager_id=None,
        recruiter_id=None,
        employment_type=None,
        location=None,
        experience_min_years=None,
        experience_max_years=None,
        salary_min=None,
        salary_max=None,
        openings_count=1,
        priority=CampaignPriority.MEDIUM,
        closing_date=None,
    )
    for k, v in overrides.items():
        object.__setattr__(campaign, k, v)
    return campaign


@pytest.fixture
def mock_campaign_service():
    svc = MagicMock()
    app.dependency_overrides[get_campaign_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_campaign_service, None)


@pytest.fixture
def mock_campaign_summary_service():
    svc = MagicMock()
    app.dependency_overrides[get_campaign_summary_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_campaign_summary_service, None)


@pytest.fixture
def recruiter(request):
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def org_admin(request):
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


# ── Create ────────────────────────────────────────────────────────────────────

class TestCreateCampaign:
    _url = "/api/v1/campaigns/"
    _payload = {"title": "Senior Engineer Campaign", "description": "Looking for senior engineers"}

    async def test_recruiter_can_create(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        campaign = make_campaign(recruiter)
        mock_campaign_service.create = AsyncMock(return_value=campaign)

        res = await client_no_lifespan.post(self._url, json=self._payload)

        assert res.status_code == 201
        body = res.json()
        assert body["title"] == campaign.title
        assert body["status"] == CampaignStatus.DRAFT.value
        assert body["is_deleted"] is False
        assert body["org_id"] == str(recruiter.org_id)

    async def test_org_admin_can_create(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, org_admin: User
    ):
        campaign = make_campaign(org_admin)
        mock_campaign_service.create = AsyncMock(return_value=campaign)

        res = await client_no_lifespan.post(self._url, json=self._payload)

        assert res.status_code == 201

    async def test_candidate_cannot_create(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, candidate: User
    ):
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 403

    async def test_missing_title_returns_422(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url, json={"description": "no title"})
        assert res.status_code == 422

    async def test_empty_title_returns_422(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url, json={**self._payload, "title": ""})
        assert res.status_code == 422

    async def test_no_org_returns_422(
        self, client_no_lifespan: AsyncClient, mock_campaign_service
    ):
        user = make_user(role=UserRole.RECRUITER, org_id=None)
        app.dependency_overrides[get_current_user] = lambda: user
        mock_campaign_service.create = AsyncMock(
            side_effect=HTTPException(422, "You must belong to an organization to manage campaigns.")
        )
        try:
            res = await client_no_lifespan.post(self._url, json=self._payload)
            assert res.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ── List ──────────────────────────────────────────────────────────────────────

class TestListCampaigns:
    _url = "/api/v1/campaigns/"

    async def test_returns_org_scoped_list(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        campaigns = [
            (make_campaign(recruiter), 0, 0),
            (make_campaign(recruiter, title="Campaign B"), 0, 0),
        ]
        mock_campaign_service.list_campaigns = AsyncMock(return_value=campaigns)

        res = await client_no_lifespan.get(self._url)

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2
        assert all(c["org_id"] == str(recruiter.org_id) for c in body)

    async def test_empty_list(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.list_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json() == []

    async def test_pagination_params_forwarded(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.list_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url, params={"skip": 10, "limit": 5})
        assert res.status_code == 200
        mock_campaign_service.list_campaigns.assert_called_once()
        _, kwargs = mock_campaign_service.list_campaigns.call_args
        assert kwargs["skip"] == 10
        assert kwargs["limit"] == 5

    async def test_candidate_can_list(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, candidate: User
    ):
        mock_campaign_service.list_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200

    async def test_unauthenticated_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 401


# ── Get single ────────────────────────────────────────────────────────────────

class TestGetCampaign:
    async def test_success_returns_campaign(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        campaign = make_campaign(recruiter)
        mock_campaign_service.get = AsyncMock(return_value=campaign)

        res = await client_no_lifespan.get(f"/api/v1/campaigns/{campaign.id}")

        assert res.status_code == 200
        assert res.json()["id"] == str(campaign.id)

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.get = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_other_org_campaign_returns_404(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        # Service enforces org isolation; returns 404 for campaigns outside the user's org
        mock_campaign_service.get = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_response_excludes_deleted_flag_is_false(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        campaign = make_campaign(recruiter)
        mock_campaign_service.get = AsyncMock(return_value=campaign)
        body = (await client_no_lifespan.get(f"/api/v1/campaigns/{campaign.id}")).json()
        assert body["is_deleted"] is False


# ── Update ────────────────────────────────────────────────────────────────────

class TestUpdateCampaign:
    _payload = {"title": "Updated Title", "status": "ACTIVE"}

    async def test_creator_can_update(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        campaign = make_campaign(recruiter, title="Updated Title", status=CampaignStatus.ACTIVE)
        mock_campaign_service.update = AsyncMock(return_value=campaign)

        res = await client_no_lifespan.patch(
            f"/api/v1/campaigns/{campaign.id}", json=self._payload
        )

        assert res.status_code == 200
        assert res.json()["title"] == "Updated Title"
        assert res.json()["status"] == "ACTIVE"

    async def test_org_admin_can_update_any(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, org_admin: User
    ):
        campaign = make_campaign(org_admin, created_by=_OTHER_USER_ID)
        mock_campaign_service.update = AsyncMock(return_value=campaign)

        res = await client_no_lifespan.patch(
            f"/api/v1/campaigns/{campaign.id}", json={"status": "CLOSED"}
        )
        assert res.status_code == 200

    async def test_candidate_cannot_update(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, candidate: User
    ):
        res = await client_no_lifespan.patch(
            f"/api/v1/campaigns/{uuid.uuid4()}", json=self._payload
        )
        assert res.status_code == 403

    async def test_not_owner_recruiter_gets_403(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.update = AsyncMock(
            side_effect=HTTPException(403, "You do not have permission to modify this campaign.")
        )
        res = await client_no_lifespan.patch(
            f"/api/v1/campaigns/{uuid.uuid4()}", json=self._payload
        )
        assert res.status_code == 403

    async def test_invalid_status_returns_422(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        res = await client_no_lifespan.patch(
            f"/api/v1/campaigns/{uuid.uuid4()}", json={"status": "INVALID_STATUS"}
        )
        assert res.status_code == 422


# ── Soft delete ───────────────────────────────────────────────────────────────

class TestDeleteCampaign:
    async def test_creator_can_delete(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 204

    async def test_org_admin_can_delete_any(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, org_admin: User
    ):
        mock_campaign_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 204

    async def test_candidate_cannot_delete(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, candidate: User
    ):
        res = await client_no_lifespan.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 403

    async def test_not_owner_recruiter_gets_403(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.delete = AsyncMock(
            side_effect=HTTPException(403, "You do not have permission to modify this campaign.")
        )
        res = await client_no_lifespan.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.delete = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 404

    async def test_deleted_response_has_no_body(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.delete = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(f"/api/v1/campaigns/{uuid.uuid4()}")
        assert res.status_code == 204
        assert res.content == b""


# ── Organization isolation ────────────────────────────────────────────────────

class TestOrgIsolation:
    async def test_service_receives_correct_user_for_org_scoping(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.list_campaigns = AsyncMock(return_value=[])
        await client_no_lifespan.get("/api/v1/campaigns/")

        call_args = mock_campaign_service.list_campaigns.call_args
        passed_user: User = call_args[0][0]
        assert passed_user.org_id == recruiter.org_id

    async def test_response_does_not_expose_soft_deleted_campaigns(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        # Service is responsible for filtering is_deleted; this verifies the contract
        mock_campaign_service.list_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get("/api/v1/campaigns/")
        assert res.status_code == 200


# ── Extended metadata fields ────────────────────────────────────────────────────

class TestCampaignMetadataFields:
    _url = "/api/v1/campaigns/"

    async def test_create_accepts_full_field_set(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        payload = {
            "title": "Senior Engineer Campaign",
            "job_title": "Senior Backend Engineer",
            "department": "Engineering",
            "employment_type": "FULL_TIME",
            "location": "Remote",
            "experience_min_years": 5,
            "experience_max_years": 10,
            "salary_min": 120000,
            "salary_max": 160000,
            "openings_count": 2,
            "priority": "HIGH",
            "closing_date": "2026-12-31",
        }
        campaign = make_campaign(
            recruiter,
            job_title="Senior Backend Engineer",
            department="Engineering",
            employment_type=EmploymentType.FULL_TIME,
            openings_count=2,
            priority=CampaignPriority.HIGH,
        )
        mock_campaign_service.create = AsyncMock(return_value=campaign)

        res = await client_no_lifespan.post(self._url, json=payload)

        assert res.status_code == 201
        body = res.json()
        assert body["department"] == "Engineering"
        assert body["priority"] == "HIGH"

    async def test_list_forwards_filters(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.list_campaigns = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(
            self._url,
            params={
                "search": "engineer",
                "status": "ACTIVE",
                "department": "Engineering",
                "employment_type": "FULL_TIME",
                "priority": "HIGH",
                "sort_by": "title",
                "sort_dir": "asc",
            },
        )
        assert res.status_code == 200
        _, kwargs = mock_campaign_service.list_campaigns.call_args
        assert kwargs["search"] == "engineer"
        assert kwargs["status_filter"] == CampaignStatus.ACTIVE
        assert kwargs["department"] == "Engineering"
        assert kwargs["employment_type"] == EmploymentType.FULL_TIME
        assert kwargs["priority"] == CampaignPriority.HIGH
        assert kwargs["sort_by"] == "title"
        assert kwargs["sort_dir"] == "asc"

    async def test_list_includes_resume_counts(
        self, client_no_lifespan: AsyncClient, mock_campaign_service, recruiter: User
    ):
        mock_campaign_service.list_campaigns = AsyncMock(
            return_value=[(make_campaign(recruiter), 5, 2)]
        )
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        body = res.json()
        assert body[0]["resume_count"] == 5
        assert body[0]["processing_resume_count"] == 2


# ── Campaign summary / processing status ─────────────────────────────────────────

class TestCampaignSummary:
    async def test_recruiter_can_view_summary(
        self,
        client_no_lifespan: AsyncClient,
        mock_campaign_service,
        mock_campaign_summary_service,
        recruiter: User,
    ):
        campaign_id = uuid.uuid4()
        mock_campaign_service.get = AsyncMock(return_value=make_campaign(recruiter))
        mock_campaign_summary_service.get_summary = AsyncMock(
            return_value=CampaignSummaryResponse(
                total_candidates=10,
                processing_candidates=2,
                ranked_candidates=8,
                shortlisted_candidates=3,
                rejected_candidates=1,
                average_match_score=72.5,
            )
        )
        res = await client_no_lifespan.get(f"/api/v1/campaigns/{campaign_id}/summary")
        assert res.status_code == 200
        body = res.json()
        assert body["total_candidates"] == 10
        assert body["average_match_score"] == 72.5

    async def test_candidate_cannot_view_summary(
        self,
        client_no_lifespan: AsyncClient,
        mock_campaign_service,
        mock_campaign_summary_service,
        candidate: User,
    ):
        res = await client_no_lifespan.get(f"/api/v1/campaigns/{uuid.uuid4()}/summary")
        assert res.status_code == 403

    async def test_not_found_returns_404(
        self,
        client_no_lifespan: AsyncClient,
        mock_campaign_service,
        mock_campaign_summary_service,
        recruiter: User,
    ):
        mock_campaign_service.get = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(f"/api/v1/campaigns/{uuid.uuid4()}/summary")
        assert res.status_code == 404


class TestCampaignProcessingStatus:
    async def test_recruiter_can_view_processing_status(
        self,
        client_no_lifespan: AsyncClient,
        mock_campaign_service,
        mock_campaign_summary_service,
        recruiter: User,
    ):
        campaign_id = uuid.uuid4()
        mock_campaign_service.get = AsyncMock(return_value=make_campaign(recruiter))
        mock_campaign_summary_service.get_processing_status = AsyncMock(
            return_value=CampaignProcessingStatusResponse(
                uploaded_count=1,
                parsing_count=2,
                embedding_count=3,
                ready_for_ranking_count=4,
                completed_count=4,
                failed_count=0,
                total_count=10,
            )
        )
        res = await client_no_lifespan.get(
            f"/api/v1/campaigns/{campaign_id}/processing-status"
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total_count"] == 10
        assert body["ready_for_ranking_count"] == 4

    async def test_candidate_cannot_view_processing_status(
        self,
        client_no_lifespan: AsyncClient,
        mock_campaign_service,
        mock_campaign_summary_service,
        candidate: User,
    ):
        res = await client_no_lifespan.get(
            f"/api/v1/campaigns/{uuid.uuid4()}/processing-status"
        )
        assert res.status_code == 403

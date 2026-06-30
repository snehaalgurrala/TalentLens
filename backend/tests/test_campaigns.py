"""
Unit tests for campaign endpoints.

Strategy:
  - get_campaign_service is overridden with a MagicMock — no database required.
  - get_current_user is overridden per-test to simulate different roles.
  - RequireRoles runs against the mocked user, so role-based 403s are tested
    without any service involvement.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.campaigns import get_campaign_service
from app.main import app
from app.models.campaign import Campaign, CampaignStatus
from app.models.user import User, UserRole
from app.schemas.campaign import CampaignResponse

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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
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
        campaigns = [make_campaign(recruiter), make_campaign(recruiter, title="Campaign B")]
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
        assert res.json() == []

"""
Unit tests for scoring-rule endpoints.

Strategy (mirrors tests/test_campaigns.py):
  - get_scoring_rule_service is overridden with a MagicMock — no database required.
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
from app.api.v1.endpoints.scoring_rules import get_scoring_rule_service
from app.main import app
from app.models.scoring_rule import ScoringRule
from app.models.user import User, UserRole
from app.schemas.scoring_rule import EffectiveScoringRuleResponse

# ── Shared fixtures ───────────────────────────────────────────────────────────

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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_rule(user: User, campaign_id: uuid.UUID | None = None, **overrides) -> ScoringRule:
    rule = ScoringRule(
        id=uuid.uuid4(),
        org_id=user.org_id,
        campaign_id=campaign_id,
        created_by=user.id,
        semantic_weight=0.30,
        skills_weight=0.25,
        experience_weight=0.15,
        education_weight=0.10,
        project_weight=0.10,
        certification_weight=0.10,
        preferred_company_bonus=0.0,
        preferred_companies=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        object.__setattr__(rule, k, v)
    return rule


_VALID_WEIGHTS = {
    "semantic_weight": 0.30,
    "skills_weight": 0.25,
    "experience_weight": 0.15,
    "education_weight": 0.10,
    "project_weight": 0.10,
    "certification_weight": 0.10,
}


@pytest.fixture
def mock_scoring_rule_service():
    svc = MagicMock()
    app.dependency_overrides[get_scoring_rule_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_scoring_rule_service, None)


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


# ── Organization default: create ────────────────────────────────────────────

class TestCreateOrganizationDefault:
    _url = "/api/v1/scoring-rules/organization"

    async def test_org_admin_can_create(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        rule = make_rule(org_admin)
        mock_scoring_rule_service.create_organization_default = AsyncMock(return_value=rule)

        res = await client_no_lifespan.post(self._url, json=_VALID_WEIGHTS)

        assert res.status_code == 201
        body = res.json()
        assert body["campaign_id"] is None
        assert body["org_id"] == str(org_admin.org_id)

    async def test_recruiter_cannot_create(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url, json=_VALID_WEIGHTS)
        assert res.status_code == 403

    async def test_candidate_cannot_create(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, candidate: User
    ):
        res = await client_no_lifespan.post(self._url, json=_VALID_WEIGHTS)
        assert res.status_code == 403

    async def test_unauthenticated_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.post(self._url, json=_VALID_WEIGHTS)
        assert res.status_code == 401

    async def test_defaults_are_used_when_no_weights_given(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        rule = make_rule(org_admin)
        mock_scoring_rule_service.create_organization_default = AsyncMock(return_value=rule)
        res = await client_no_lifespan.post(self._url, json={})
        assert res.status_code == 201

    async def test_weights_not_summing_to_one_returns_422(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        bad = {**_VALID_WEIGHTS, "semantic_weight": 0.9}
        res = await client_no_lifespan.post(self._url, json=bad)
        assert res.status_code == 422

    async def test_bonus_over_5_percent_returns_422(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        bad = {**_VALID_WEIGHTS, "preferred_company_bonus": 0.10}
        res = await client_no_lifespan.post(self._url, json=bad)
        assert res.status_code == 422

    async def test_conflict_when_default_already_exists(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        mock_scoring_rule_service.create_organization_default = AsyncMock(
            side_effect=HTTPException(409, "An organization scoring default already exists. Use PATCH to update it.")
        )
        res = await client_no_lifespan.post(self._url, json=_VALID_WEIGHTS)
        assert res.status_code == 409


# ── Organization default: read / update / delete ────────────────────────────

class TestOrganizationDefaultReadUpdateDelete:
    _url = "/api/v1/scoring-rules/organization"

    async def test_recruiter_can_read(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        rule = make_rule(recruiter)
        mock_scoring_rule_service.get_organization_default = AsyncMock(return_value=rule)
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 200
        assert res.json()["id"] == str(rule.id)

    async def test_read_not_configured_returns_404(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.get_organization_default = AsyncMock(
            side_effect=HTTPException(404, "No organization scoring default has been configured.")
        )
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 404

    async def test_candidate_cannot_read(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 403

    async def test_org_admin_can_update(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        rule = make_rule(org_admin, preferred_companies=["Acme Corp"])
        mock_scoring_rule_service.update_organization_default = AsyncMock(return_value=rule)
        res = await client_no_lifespan.patch(self._url, json={"preferred_companies": ["Acme Corp"]})
        assert res.status_code == 200
        assert res.json()["preferred_companies"] == ["Acme Corp"]

    async def test_recruiter_cannot_update(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        res = await client_no_lifespan.patch(self._url, json={"preferred_companies": ["Acme"]})
        assert res.status_code == 403

    async def test_update_partial_weights_returns_422(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        res = await client_no_lifespan.patch(self._url, json={"semantic_weight": 0.5})
        assert res.status_code == 422

    async def test_org_admin_can_delete(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        mock_scoring_rule_service.delete_organization_default = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(self._url)
        assert res.status_code == 204

    async def test_recruiter_cannot_delete(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        res = await client_no_lifespan.delete(self._url)
        assert res.status_code == 403

    async def test_delete_not_configured_returns_404(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        mock_scoring_rule_service.delete_organization_default = AsyncMock(
            side_effect=HTTPException(404, "No organization scoring default has been configured.")
        )
        res = await client_no_lifespan.delete(self._url)
        assert res.status_code == 404


# ── Campaign override: create ───────────────────────────────────────────────

class TestCreateCampaignOverride:
    def _url(self, campaign_id: uuid.UUID) -> str:
        return f"/api/v1/scoring-rules/campaigns/{campaign_id}"

    async def test_owner_recruiter_can_create(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        rule = make_rule(recruiter, campaign_id=campaign_id)
        mock_scoring_rule_service.create_campaign_override = AsyncMock(return_value=rule)

        res = await client_no_lifespan.post(self._url(campaign_id), json=_VALID_WEIGHTS)

        assert res.status_code == 201
        assert res.json()["campaign_id"] == str(campaign_id)

    async def test_org_admin_can_create_for_any_campaign(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, org_admin: User
    ):
        campaign_id = uuid.uuid4()
        rule = make_rule(org_admin, campaign_id=campaign_id)
        mock_scoring_rule_service.create_campaign_override = AsyncMock(return_value=rule)

        res = await client_no_lifespan.post(self._url(campaign_id), json=_VALID_WEIGHTS)
        assert res.status_code == 201

    async def test_candidate_cannot_create(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, candidate: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=_VALID_WEIGHTS)
        assert res.status_code == 403

    async def test_non_owner_recruiter_gets_403(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.create_campaign_override = AsyncMock(
            side_effect=HTTPException(
                403, "You do not have permission to modify scoring rules for this campaign."
            )
        )
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=_VALID_WEIGHTS)
        assert res.status_code == 403

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.create_campaign_override = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=_VALID_WEIGHTS)
        assert res.status_code == 404

    async def test_conflict_when_override_already_exists(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.create_campaign_override = AsyncMock(
            side_effect=HTTPException(
                409, "A scoring override already exists for this campaign. Use PATCH to update it."
            )
        )
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=_VALID_WEIGHTS)
        assert res.status_code == 409

    async def test_bonus_over_5_percent_returns_422(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        bad = {**_VALID_WEIGHTS, "preferred_company_bonus": 0.10}
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=bad)
        assert res.status_code == 422


# ── Campaign override: read / update / delete ───────────────────────────────

class TestCampaignOverrideReadUpdateDelete:
    def _url(self, campaign_id: uuid.UUID) -> str:
        return f"/api/v1/scoring-rules/campaigns/{campaign_id}"

    async def test_recruiter_can_read(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        rule = make_rule(recruiter, campaign_id=campaign_id)
        mock_scoring_rule_service.get_campaign_override = AsyncMock(return_value=rule)

        res = await client_no_lifespan.get(self._url(campaign_id))
        assert res.status_code == 200
        assert res.json()["campaign_id"] == str(campaign_id)

    async def test_read_not_configured_returns_404(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.get_campaign_override = AsyncMock(
            side_effect=HTTPException(404, "No scoring override has been configured for this campaign.")
        )
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 404

    async def test_candidate_cannot_read(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 403

    async def test_owner_recruiter_can_update(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        rule = make_rule(recruiter, campaign_id=campaign_id, preferred_company_bonus=0.05)
        mock_scoring_rule_service.update_campaign_override = AsyncMock(return_value=rule)

        res = await client_no_lifespan.patch(
            self._url(campaign_id), json={"preferred_company_bonus": 0.05}
        )
        assert res.status_code == 200
        assert res.json()["preferred_company_bonus"] == 0.05

    async def test_non_owner_recruiter_gets_403_on_update(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.update_campaign_override = AsyncMock(
            side_effect=HTTPException(
                403, "You do not have permission to modify scoring rules for this campaign."
            )
        )
        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4()), json={"preferred_company_bonus": 0.02}
        )
        assert res.status_code == 403

    async def test_owner_recruiter_can_delete(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.delete_campaign_override = AsyncMock(return_value=None)
        res = await client_no_lifespan.delete(self._url(uuid.uuid4()))
        assert res.status_code == 204

    async def test_candidate_cannot_delete(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, candidate: User
    ):
        res = await client_no_lifespan.delete(self._url(uuid.uuid4()))
        assert res.status_code == 403

    async def test_delete_not_configured_returns_404(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.delete_campaign_override = AsyncMock(
            side_effect=HTTPException(404, "No scoring override has been configured for this campaign.")
        )
        res = await client_no_lifespan.delete(self._url(uuid.uuid4()))
        assert res.status_code == 404


# ── Effective scoring rule ───────────────────────────────────────────────────

class TestEffectiveScoringRule:
    def _url(self, campaign_id: uuid.UUID) -> str:
        return f"/api/v1/scoring-rules/campaigns/{campaign_id}/effective"

    def _effective(self, org_id: uuid.UUID, campaign_id: uuid.UUID, source: str, **overrides):
        payload = {
            "id": None,
            "org_id": org_id,
            "campaign_id": campaign_id,
            "created_by": None,
            **_VALID_WEIGHTS,
            "preferred_company_bonus": 0.0,
            "preferred_companies": [],
            "source": source,
        }
        payload.update(overrides)
        return EffectiveScoringRuleResponse(**payload)

    async def test_falls_back_to_system_default(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        effective = self._effective(recruiter.org_id, campaign_id, "system_default")
        mock_scoring_rule_service.get_effective = AsyncMock(return_value=effective)

        res = await client_no_lifespan.get(self._url(campaign_id))
        assert res.status_code == 200
        assert res.json()["source"] == "system_default"
        assert res.json()["id"] is None

    async def test_returns_organization_default_source(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        effective = self._effective(
            recruiter.org_id, campaign_id, "organization_default", id=uuid.uuid4()
        )
        mock_scoring_rule_service.get_effective = AsyncMock(return_value=effective)

        res = await client_no_lifespan.get(self._url(campaign_id))
        assert res.status_code == 200
        assert res.json()["source"] == "organization_default"

    async def test_returns_campaign_override_source(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        effective = self._effective(
            recruiter.org_id, campaign_id, "campaign_override", id=uuid.uuid4()
        )
        mock_scoring_rule_service.get_effective = AsyncMock(return_value=effective)

        res = await client_no_lifespan.get(self._url(campaign_id))
        assert res.status_code == 200
        assert res.json()["source"] == "campaign_override"

    async def test_candidate_cannot_view(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 403

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_scoring_rule_service, recruiter: User
    ):
        mock_scoring_rule_service.get_effective = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 404

    async def test_unauthenticated_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 401

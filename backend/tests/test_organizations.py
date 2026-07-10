"""
Unit tests for organization bootstrap and invitation endpoints.

Strategy (matches test_campaigns.py):
  - get_organization_service is overridden with a MagicMock — no database
    required.
  - get_current_user is overridden per-test to simulate different roles.
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.organizations import get_organization_service
from app.main import app
from app.models.organization import Organization
from app.models.organization_invitation import InvitationStatus, OrganizationInvitation
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse

_ORG_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.ORG_ADMIN, org_id: uuid.UUID | None = _ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        full_name="Admin User",
        password_hash="$2b$12$irrelevant",
        role=role,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_org(**overrides) -> Organization:
    org = Organization(
        id=_ORG_ID,
        name="Acme Corp",
        slug="acme-corp",
        is_active=True,
        timezone="UTC",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    for k, v in overrides.items():
        object.__setattr__(org, k, v)
    return org


def make_invitation(**overrides) -> OrganizationInvitation:
    inv = OrganizationInvitation(
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        email="recruiter@example.com",
        token_hash="deadbeef",
        status=InvitationStatus.PENDING,
        invited_by=uuid.uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=7),
        accepted_at=None,
        created_at=datetime.now(UTC),
    )
    for k, v in overrides.items():
        object.__setattr__(inv, k, v)
    return inv


def fake_tokens() -> TokenResponse:
    return TokenResponse(access_token="fake-access", refresh_token="fake-refresh")


@pytest.fixture
def mock_org_service():
    svc = MagicMock()
    app.dependency_overrides[get_organization_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_organization_service, None)


@pytest.fixture
def org_admin():
    user = make_user(role=UserRole.ORG_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


# ── Bootstrap ────────────────────────────────────────────────────────────────


class TestBootstrap:
    _url = "/api/v1/organizations/bootstrap"
    _payload = {
        "org_name": "Acme Corp",
        "org_slug": "acme-corp",
        "admin_email": "admin@example.com",
        "admin_password": "securepass1",
        "admin_full_name": "Admin User",
    }

    async def test_success_returns_201(
        self, client_no_lifespan: AsyncClient, mock_org_service
    ):
        org = make_org()
        admin = make_user(role=UserRole.ORG_ADMIN)
        mock_org_service.bootstrap = AsyncMock(return_value=(org, admin, fake_tokens()))

        res = await client_no_lifespan.post(self._url, json=self._payload)

        assert res.status_code == 201
        body = res.json()
        assert body["organization"]["slug"] == "acme-corp"
        assert body["admin"]["role"] == "ORG_ADMIN"
        assert body["tokens"]["access_token"] == "fake-access"

    async def test_duplicate_slug_returns_409(
        self, client_no_lifespan: AsyncClient, mock_org_service
    ):
        mock_org_service.bootstrap = AsyncMock(
            side_effect=HTTPException(409, "An organization with this slug already exists.")
        )
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 409

    async def test_invalid_slug_returns_422(
        self, client_no_lifespan: AsyncClient, mock_org_service
    ):
        res = await client_no_lifespan.post(
            self._url, json={**self._payload, "org_slug": "Not A Valid Slug!"}
        )
        assert res.status_code == 422

    async def test_short_password_returns_422(
        self, client_no_lifespan: AsyncClient, mock_org_service
    ):
        res = await client_no_lifespan.post(
            self._url, json={**self._payload, "admin_password": "short"}
        )
        assert res.status_code == 422


# ── Invitations ────────────────────────────────────────────────────────────


class TestInvite:
    _url = f"/api/v1/organizations/{_ORG_ID}/invitations"
    _payload = {"email": "recruiter@example.com"}

    async def test_org_admin_can_invite(
        self, client_no_lifespan: AsyncClient, mock_org_service, org_admin
    ):
        invitation = make_invitation()
        mock_org_service.invite = AsyncMock(return_value=(invitation, "raw-token-value"))

        res = await client_no_lifespan.post(self._url, json=self._payload)

        assert res.status_code == 201
        body = res.json()
        assert body["email"] == "recruiter@example.com"
        assert body["token"] == "raw-token-value"
        assert body["status"] == "PENDING"

    async def test_recruiter_cannot_invite(
        self, client_no_lifespan: AsyncClient, mock_org_service, recruiter
    ):
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 403

    async def test_org_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_org_service, org_admin
    ):
        mock_org_service.invite = AsyncMock(
            side_effect=HTTPException(404, "Organization not found.")
        )
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 404

    async def test_admin_of_different_org_returns_403(
        self, client_no_lifespan: AsyncClient, mock_org_service, org_admin
    ):
        mock_org_service.invite = AsyncMock(
            side_effect=HTTPException(
                403, "You do not have permission to invite recruiters to this organization."
            )
        )
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 403

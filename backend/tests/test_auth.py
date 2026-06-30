"""
Unit tests for auth endpoints and protected routes.

Strategy:
  - Auth endpoint tests override the `get_auth_service` dependency with a
    MagicMock so no database is needed.
  - Protected-route tests either hit the real `get_current_user` with a
    deliberately bad token (expects 401), or override `get_current_user`
    with a mock user fixture (expects 200).
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.auth import get_auth_service
from app.main import app
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(**overrides) -> User:
    """Build a detached (no session) User instance for testing."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        password_hash="$2b$12$irrelevant",
        role=UserRole.CANDIDATE,
        org_id=None,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        object.__setattr__(user, k, v)
    return user


def fake_tokens() -> TokenResponse:
    return TokenResponse(access_token="fake-access", refresh_token="fake-refresh")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_auth_service():
    """Override get_auth_service with a MagicMock for the duration of a test."""
    svc = MagicMock()
    app.dependency_overrides[get_auth_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_auth_service, None)


@pytest.fixture
def mock_current_user():
    """Override get_current_user to return a synthetic User (no DB required)."""
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegister:
    _url = "/api/v1/auth/register"
    _payload = {
        "email": "new@example.com",
        "password": "securepass1",
        "full_name": "New User",
    }

    async def test_success_returns_201_with_tokens(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        user = make_user(email="new@example.com")
        mock_auth_service.register = AsyncMock(return_value=(user, fake_tokens()))

        res = await client_no_lifespan.post(self._url, json=self._payload)

        assert res.status_code == 201
        body = res.json()
        assert body["access_token"] == "fake-access"
        assert body["refresh_token"] == "fake-refresh"
        assert body["token_type"] == "bearer"

    async def test_duplicate_email_returns_409(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        mock_auth_service.register = AsyncMock(
            side_effect=HTTPException(409, "An account with this email already exists.")
        )
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 409

    async def test_short_password_returns_422(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        res = await client_no_lifespan.post(
            self._url, json={**self._payload, "password": "short"}
        )
        assert res.status_code == 422

    async def test_invalid_email_returns_422(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        res = await client_no_lifespan.post(
            self._url, json={**self._payload, "email": "not-an-email"}
        )
        assert res.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    _url = "/api/v1/auth/login"
    _payload = {"email": "test@example.com", "password": "correctpassword"}

    async def test_success_returns_tokens(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        user = make_user()
        mock_auth_service.login = AsyncMock(return_value=(user, fake_tokens()))

        res = await client_no_lifespan.post(self._url, json=self._payload)

        assert res.status_code == 200
        assert res.json()["access_token"] == "fake-access"

    async def test_wrong_password_returns_401(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        mock_auth_service.login = AsyncMock(
            side_effect=HTTPException(401, "Invalid email or password.")
        )
        res = await client_no_lifespan.post(
            self._url, json={**self._payload, "password": "wrong"}
        )
        assert res.status_code == 401

    async def test_nonexistent_user_returns_401(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        mock_auth_service.login = AsyncMock(
            side_effect=HTTPException(401, "Invalid email or password.")
        )
        res = await client_no_lifespan.post(
            self._url, json={"email": "ghost@example.com", "password": "anything"}
        )
        assert res.status_code == 401

    async def test_inactive_account_returns_403(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        mock_auth_service.login = AsyncMock(
            side_effect=HTTPException(403, "This account has been deactivated.")
        )
        res = await client_no_lifespan.post(self._url, json=self._payload)
        assert res.status_code == 403


# ── Token refresh ─────────────────────────────────────────────────────────────

class TestRefresh:
    _url = "/api/v1/auth/refresh"

    async def test_valid_refresh_returns_new_tokens(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        new_tokens = TokenResponse(access_token="new-access", refresh_token="new-refresh")
        mock_auth_service.refresh = AsyncMock(return_value=new_tokens)

        res = await client_no_lifespan.post(self._url, json={"refresh_token": "some-token"})

        assert res.status_code == 200
        assert res.json()["access_token"] == "new-access"

    async def test_invalid_refresh_token_returns_401(
        self, client_no_lifespan: AsyncClient, mock_auth_service
    ):
        mock_auth_service.refresh = AsyncMock(
            side_effect=HTTPException(401, "Invalid or expired refresh token.")
        )
        res = await client_no_lifespan.post(self._url, json={"refresh_token": "expired"})
        assert res.status_code == 401


# ── Protected routes ──────────────────────────────────────────────────────────

class TestProtectedRoutes:
    _url = "/api/v1/users/me"

    async def test_no_token_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(self._url)
        assert res.status_code == 401

    async def test_malformed_token_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(
            self._url, headers={"Authorization": "Bearer this.is.garbage"}
        )
        assert res.status_code == 401

    async def test_wrong_scheme_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(
            self._url, headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert res.status_code == 401

    async def test_authenticated_user_returns_profile(
        self,
        client_no_lifespan: AsyncClient,
        mock_current_user: User,
    ):
        # get_current_user is overridden by the fixture; any bearer value is accepted
        res = await client_no_lifespan.get(
            self._url, headers={"Authorization": "Bearer any-token"}
        )

        assert res.status_code == 200
        body = res.json()
        assert body["email"] == mock_current_user.email
        assert body["full_name"] == mock_current_user.full_name
        assert body["role"] == mock_current_user.role.value
        assert body["is_active"] is True
        assert body["org_id"] is None

    async def test_response_does_not_expose_password_hash(
        self,
        client_no_lifespan: AsyncClient,
        mock_current_user: User,
    ):
        res = await client_no_lifespan.get(
            self._url, headers={"Authorization": "Bearer any-token"}
        )
        assert "password_hash" not in res.json()
        assert "refresh_token_hash" not in res.json()

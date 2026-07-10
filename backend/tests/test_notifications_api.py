"""Unit tests for the /notifications REST endpoints. NotificationService is
mocked via dependency override — mirrors test_assessment_analytics_api.py.
The SSE stream endpoint's live-push behavior is exercised manually (Redis
Pub/Sub across processes isn't practical to unit test here); only its
query-token auth guard is covered.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.notifications import get_notification_service
from app.main import app
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole

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


def make_notification(**overrides) -> Notification:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        user_id=uuid.uuid4(),
        type=NotificationType.SUCCESS,
        title="Assessment Completed",
        message="Jane Doe completed their assessment.",
        resume_file_id=uuid.uuid4(),
        is_read=False,
        created_at=now,
    )
    defaults.update(overrides)
    return Notification(**defaults)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_notification_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_notification_service, None)


@pytest.fixture
def current_user():
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestListNotifications:
    async def test_returns_notifications(
        self, client_no_lifespan: AsyncClient, mock_service, current_user: User
    ):
        notification = make_notification(user_id=current_user.id)
        mock_service.list_for_user = AsyncMock(return_value=[notification])

        res = await client_no_lifespan.get("/api/v1/notifications/")

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 1
        assert body[0]["title"] == "Assessment Completed"
        mock_service.list_for_user.assert_awaited_once_with(current_user.id)


class TestUpdateNotification:
    async def test_marks_read(self, client_no_lifespan: AsyncClient, mock_service, current_user: User):
        notification = make_notification(user_id=current_user.id, is_read=True)
        mock_service.mark_read = AsyncMock(return_value=notification)

        res = await client_no_lifespan.patch(
            f"/api/v1/notifications/{notification.id}", json={"is_read": True}
        )

        assert res.status_code == 200
        assert res.json()["is_read"] is True

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, current_user: User
    ):
        mock_service.mark_read = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Notification not found.")
        )

        res = await client_no_lifespan.patch(
            f"/api/v1/notifications/{uuid.uuid4()}", json={"is_read": True}
        )

        assert res.status_code == 404


class TestMarkAllRead:
    async def test_returns_204(self, client_no_lifespan: AsyncClient, mock_service, current_user: User):
        mock_service.mark_all_read = AsyncMock(return_value=2)

        res = await client_no_lifespan.post("/api/v1/notifications/mark-all-read")

        assert res.status_code == 204
        mock_service.mark_all_read.assert_awaited_once_with(current_user.id)


class TestStreamAuth:
    async def test_missing_token_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get("/api/v1/notifications/stream")
        assert res.status_code == 401

    async def test_invalid_token_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(
            "/api/v1/notifications/stream", params={"token": "garbage"}
        )
        assert res.status_code == 401

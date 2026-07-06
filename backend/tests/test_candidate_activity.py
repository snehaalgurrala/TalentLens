"""
Unit tests for the candidate activity endpoint: GET /candidates/{id}/activity.

Strategy mirrors test_candidate_management.py: CandidateActivityService is
mocked via dependency override, get_current_user is overridden per-test.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.candidate_profile import get_candidate_activity_service
from app.main import app
from app.models.candidate_activity import ActivityEventType, CandidateActivity
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


def make_activity(event_type: ActivityEventType, **overrides) -> CandidateActivity:
    activity = CandidateActivity(
        id=overrides.get("id", uuid.uuid4()),
        resume_file_id=overrides.get("resume_file_id", uuid.uuid4()),
        actor_id=overrides.get("actor_id"),
        event_type=event_type,
        event_metadata=overrides.get("event_metadata"),
        created_at=overrides.get("created_at", datetime.now(UTC)),
    )
    # `actor` is lazy="raise" — a transient object needs it explicitly set
    # (even to None) or Pydantic's from_attributes read will trigger a raise.
    activity.actor = overrides.get("actor")
    return activity


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_candidate_activity_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_candidate_activity_service, None)


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


class TestListActivity:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/activity"

    async def test_returns_timeline_newest_first(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        uploaded = make_activity(ActivityEventType.RESUME_UPLOADED)
        shortlisted = make_activity(
            ActivityEventType.SHORTLISTED, actor_id=recruiter.id
        )
        mock_service.list = AsyncMock(return_value=[shortlisted, uploaded])

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2
        assert body[0]["event_type"] == "SHORTLISTED"
        assert body[1]["event_type"] == "RESUME_UPLOADED"
        assert body[1]["actor"] is None

    async def test_pipeline_stage_changed_includes_metadata(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        activity = make_activity(
            ActivityEventType.PIPELINE_STAGE_CHANGED,
            actor_id=recruiter.id,
            event_metadata={"from_stage": "RANKED", "to_stage": "HIRED"},
        )
        mock_service.list = AsyncMock(return_value=[activity])

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 200
        body = res.json()
        assert body[0]["event_metadata"] == {"from_stage": "RANKED", "to_stage": "HIRED"}

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.list = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Candidate not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.list.assert_not_called()

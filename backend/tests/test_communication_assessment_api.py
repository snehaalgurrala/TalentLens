"""
Unit tests for the communication assessment read endpoint:
  - GET /assessment/communication/{session_id}

Strategy mirrors test_assessment_analysis.py: CommunicationAssessmentService
is mocked via dependency override; RBAC is exercised against the CANDIDATE role.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.communication_assessment import get_communication_assessment_service
from app.main import app
from app.models.communication_assessment import (
    CommunicationAssessment,
    CommunicationAssessmentStatus,
)
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


def make_assessment(**overrides) -> CommunicationAssessment:
    now = datetime.now(UTC)
    defaults = dict(
        id=overrides.get("id", uuid.uuid4()),
        organization_id=_ORG_ID,
        assessment_session_id=overrides.get("assessment_session_id", uuid.uuid4()),
        status=overrides.get("status", CommunicationAssessmentStatus.PENDING),
        overall_score=overrides.get("overall_score"),
        reading_score=overrides.get("reading_score"),
        listening_score=overrides.get("listening_score"),
        confidence_score=overrides.get("confidence_score"),
        strengths_json=overrides.get("strengths_json"),
        improvements_json=overrides.get("improvements_json"),
        summary_json=overrides.get("summary_json"),
        error_message=overrides.get("error_message"),
        created_at=now,
        updated_at=now,
    )
    return CommunicationAssessment(**defaults)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_communication_assessment_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_communication_assessment_service, None)


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


class TestGetCommunicationAssessment:
    def _url(self, session_id: uuid.UUID) -> str:
        return f"/api/v1/assessment/communication/{session_id}"

    async def test_returns_completed_assessment(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        assessment = make_assessment(
            status=CommunicationAssessmentStatus.COMPLETED,
            overall_score=85.0,
            reading_score=90.0,
            listening_score=80.0,
            confidence_score=88.0,
            strengths_json=["Reads clearly and accurately"],
            improvements_json=["Speaking pace may be difficult to follow"],
            summary_json={"overview": "Great job overall."},
        )
        mock_service.get_assessment = AsyncMock(return_value=assessment)

        res = await client_no_lifespan.get(self._url(assessment.assessment_session_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "COMPLETED"
        assert body["overall_score"] == 85.0
        assert body["reading_score"] == 90.0
        assert body["listening_score"] == 80.0
        assert body["confidence_score"] == 88.0
        assert body["strengths_json"] == ["Reads clearly and accurately"]
        assert body["improvements_json"] == ["Speaking pace may be difficult to follow"]
        assert body["summary_json"] == {"overview": "Great job overall."}

    async def test_returns_pending_assessment_with_null_fields(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        assessment = make_assessment(status=CommunicationAssessmentStatus.PENDING)
        mock_service.get_assessment = AsyncMock(return_value=assessment)

        res = await client_no_lifespan.get(self._url(assessment.assessment_session_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "PENDING"
        assert body["overall_score"] is None

    async def test_returns_failed_assessment_with_error_message(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        assessment = make_assessment(
            status=CommunicationAssessmentStatus.FAILED,
            error_message="Read Aloud analysis failed; cannot generate communication assessment.",
        )
        mock_service.get_assessment = AsyncMock(return_value=assessment)

        res = await client_no_lifespan.get(self._url(assessment.assessment_session_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "FAILED"
        assert "Read Aloud" in body["error_message"]

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        from fastapi import HTTPException

        mock_service.get_assessment = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Communication assessment not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_assessment.assert_not_called()

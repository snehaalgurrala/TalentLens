"""
Unit tests for the assessment transcript read endpoint:
  - GET /assessment/transcripts/{recording_id}

Strategy mirrors test_assessment_sessions.py: AssessmentTranscriptService is
mocked via dependency override; RBAC is exercised against the CANDIDATE role.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.assessment_transcripts import get_assessment_transcript_service
from app.main import app
from app.models.assessment_transcript import AssessmentTranscript, TranscriptStatus
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


def make_transcript(**overrides) -> AssessmentTranscript:
    now = datetime.now(UTC)
    defaults = dict(
        id=overrides.get("id", uuid.uuid4()),
        organization_id=_ORG_ID,
        recording_id=overrides.get("recording_id", uuid.uuid4()),
        status=overrides.get("status", TranscriptStatus.PENDING),
        transcript=overrides.get("transcript"),
        language=overrides.get("language"),
        model_name=overrides.get("model_name"),
        processing_time_ms=overrides.get("processing_time_ms"),
        segment_count=overrides.get("segment_count"),
        error_message=overrides.get("error_message"),
        created_at=now,
        updated_at=now,
    )
    return AssessmentTranscript(**defaults)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_assessment_transcript_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_assessment_transcript_service, None)


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


class TestGetAssessmentTranscript:
    def _url(self, recording_id: uuid.UUID) -> str:
        return f"/api/v1/assessment/transcripts/{recording_id}"

    async def test_returns_completed_transcript(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        transcript = make_transcript(
            status=TranscriptStatus.COMPLETED,
            transcript="hello world",
            language="en",
            model_name="base",
            processing_time_ms=1500,
            segment_count=2,
        )
        mock_service.get_transcript = AsyncMock(return_value=transcript)

        res = await client_no_lifespan.get(self._url(transcript.recording_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "COMPLETED"
        assert body["transcript"] == "hello world"
        assert body["language"] == "en"
        assert body["model_name"] == "base"
        assert body["processing_time_ms"] == 1500
        assert body["segment_count"] == 2

    async def test_returns_pending_transcript_with_null_fields(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        transcript = make_transcript(status=TranscriptStatus.PENDING)
        mock_service.get_transcript = AsyncMock(return_value=transcript)

        res = await client_no_lifespan.get(self._url(transcript.recording_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "PENDING"
        assert body["transcript"] is None

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        from fastapi import HTTPException

        mock_service.get_transcript = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Transcript not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_transcript.assert_not_called()

"""
Unit tests for the recruiter assessment-dashboard endpoints:
  - GET /assessment/session/by-candidate/{candidate_id}
  - GET /assessment/session/{id}/full
  - GET /assessment/session/{id}/recordings/{recording_type}/download

Strategy mirrors test_assessment_sessions.py: AssessmentDashboardService is
mocked via dependency override; RBAC is exercised against the CANDIDATE role.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.assessment_sessions import get_assessment_dashboard_service
from app.main import app
from app.models.assessment_recording import AssessmentRecording, RecordingStatus, RecordingType
from app.models.assessment_session import (
    AssessmentSection,
    AssessmentSession,
    AssessmentSessionStatus,
)
from app.models.user import User, UserRole
from app.schemas.assessment_dashboard import (
    AssessmentRecordingDetail,
    AssessmentSessionCampaignInfo,
    AssessmentSessionCandidateInfo,
    AssessmentSessionFullResponse,
    AssessmentSessionListItem,
    AssessmentSessionListResponse,
)
from app.schemas.assessment_session import AssessmentRecordingResponse, AssessmentSessionResponse

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


def make_session(**overrides) -> AssessmentSession:
    now = datetime.now(UTC)
    defaults = dict(
        id=overrides.get("id", uuid.uuid4()),
        org_id=_ORG_ID,
        campaign_id=overrides.get("campaign_id", uuid.uuid4()),
        candidate_id=overrides.get("candidate_id", uuid.uuid4()),
        current_section=overrides.get("current_section", AssessmentSection.APTITUDE),
        current_question=overrides.get("current_question", 1),
        status=overrides.get("status", AssessmentSessionStatus.IN_PROGRESS),
        started_at=now,
        completed_at=overrides.get("completed_at"),
        created_at=now,
        updated_at=now,
    )
    return AssessmentSession(**defaults)


def make_recording(**overrides) -> AssessmentRecording:
    now = datetime.now(UTC)
    return AssessmentRecording(
        id=overrides.get("id", uuid.uuid4()),
        session_id=overrides.get("session_id", uuid.uuid4()),
        recording_type=overrides.get("recording_type", RecordingType.READ_ALOUD),
        filename=overrides.get("filename", "clip.webm"),
        mime_type=overrides.get("mime_type", "audio/webm"),
        duration_seconds=overrides.get("duration_seconds", 12.5),
        storage_path=overrides.get("storage_path", "assessment-recordings/x/read_aloud/y.webm"),
        file_size=overrides.get("file_size", 4096),
        status=overrides.get("status", RecordingStatus.UPLOADED),
        uploaded_at=overrides.get("uploaded_at", now),
        created_at=now,
        updated_at=now,
    )


def make_full_response(session: AssessmentSession, recordings: list | None = None) -> AssessmentSessionFullResponse:
    return AssessmentSessionFullResponse(
        session=AssessmentSessionResponse.model_validate(session),
        candidate=AssessmentSessionCandidateInfo(
            id=session.candidate_id, first_name="Jane", last_name="Doe", email="jane@example.com"
        ),
        campaign=AssessmentSessionCampaignInfo(id=session.campaign_id, title="Frontend Engineer"),
        pipeline_stage=None,
        recordings=[
            AssessmentRecordingDetail(
                recording=AssessmentRecordingResponse.model_validate(r),
                reference_sentence="The quick brown fox jumps over the lazy dog.",
                transcript=None,
                analysis=None,
            )
            for r in (recordings or [])
        ],
        communication_assessment=None,
    )


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_assessment_dashboard_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_assessment_dashboard_service, None)


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


class TestListSessions:
    def _url(self, campaign_id: uuid.UUID | None = None) -> str:
        base = "/api/v1/assessment/session"
        return f"{base}?campaign_id={campaign_id}" if campaign_id else base

    async def test_returns_list(self, client_no_lifespan: AsyncClient, mock_service, recruiter: User):
        session = make_session()
        item = AssessmentSessionListItem(
            session_id=session.id,
            candidate=AssessmentSessionCandidateInfo(
                id=session.candidate_id, first_name="Jane", last_name="Doe", email="jane@example.com"
            ),
            campaign=AssessmentSessionCampaignInfo(id=session.campaign_id, title="Frontend Engineer"),
            status=session.status,
            current_section=session.current_section,
            progress_percent=33,
            started_at=session.started_at,
            completed_at=session.completed_at,
            overall_score=None,
            communication_status=None,
        )
        mock_service.list_sessions = AsyncMock(
            return_value=AssessmentSessionListResponse(items=[item], total=1)
        )

        res = await client_no_lifespan.get(self._url())

        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["items"][0]["session_id"] == str(session.id)
        assert body["items"][0]["candidate"]["first_name"] == "Jane"
        assert body["items"][0]["campaign"]["title"] == "Frontend Engineer"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url())

        assert res.status_code == 403
        mock_service.list_sessions.assert_not_called()


class TestGetSessionByCandidate:
    def _url(self, candidate_id: uuid.UUID, campaign_id: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/by-candidate/{candidate_id}?campaign_id={campaign_id}"

    async def test_returns_session(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        session = make_session()
        mock_service.get_session_by_candidate = AsyncMock(return_value=session)

        res = await client_no_lifespan.get(self._url(session.candidate_id, session.campaign_id))

        assert res.status_code == 200
        assert res.json()["id"] == str(session.id)

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.get_session_by_candidate = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="No assessment session found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4(), uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4(), uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_session_by_candidate.assert_not_called()


class TestGetSessionFull:
    def _url(self, session_id: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/{session_id}/full"

    async def test_returns_full_payload_with_no_recordings(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        session = make_session()
        mock_service.get_full = AsyncMock(return_value=make_full_response(session))

        res = await client_no_lifespan.get(self._url(session.id))

        assert res.status_code == 200
        body = res.json()
        assert body["session"]["id"] == str(session.id)
        assert body["recordings"] == []
        assert body["communication_assessment"] is None

    async def test_returns_full_payload_with_recordings(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        session = make_session()
        recording = make_recording(session_id=session.id)
        mock_service.get_full = AsyncMock(return_value=make_full_response(session, [recording]))

        res = await client_no_lifespan.get(self._url(session.id))

        assert res.status_code == 200
        body = res.json()
        assert len(body["recordings"]) == 1
        assert body["recordings"][0]["recording"]["id"] == str(recording.id)
        assert body["recordings"][0]["reference_sentence"]
        assert body["recordings"][0]["transcript"] is None
        assert body["recordings"][0]["analysis"] is None

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.get_full = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Assessment session not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_full.assert_not_called()


class TestDownloadRecording:
    def _url(self, session_id: uuid.UUID, recording_type: str = "READ_ALOUD") -> str:
        return f"/api/v1/assessment/session/{session_id}/recordings/{recording_type}/download"

    async def test_streams_audio_bytes(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        from app.storage.factory import get_storage_backend

        session = make_session()
        recording = make_recording(session_id=session.id)
        mock_service.get_recording_audio = AsyncMock(return_value=recording)

        fake_storage = MagicMock()
        fake_storage.load = AsyncMock(return_value=b"audio-bytes")
        app.dependency_overrides[get_storage_backend] = lambda: fake_storage
        try:
            res = await client_no_lifespan.get(self._url(session.id))
        finally:
            app.dependency_overrides.pop(get_storage_backend, None)

        assert res.status_code == 200
        assert res.content == b"audio-bytes"
        assert res.headers["content-type"] == "audio/webm"
        assert "clip.webm" in res.headers["content-disposition"]

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.get_recording_audio = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Recording not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_recording_audio.assert_not_called()

"""
Unit tests for the assessment session endpoints:
  - POST /assessment/session
  - GET/PATCH /assessment/session/{id}
  - POST /assessment/session/{id}/answers
  - POST /assessment/session/{id}/recordings
  - POST /assessment/session/{id}/complete

Strategy mirrors test_candidate_tasks.py: AssessmentSessionService is mocked
via dependency override; RBAC is exercised against the CANDIDATE role.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.assessment_sessions import (
    get_assessment_session_service,
    resolve_recording_upload_org_id,
)
from app.main import app
from app.models.assessment_answer import AssessmentAnswer
from app.models.assessment_recording import AssessmentRecording, RecordingStatus, RecordingType
from app.models.assessment_session import (
    AssessmentSection,
    AssessmentSession,
    AssessmentSessionStatus,
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


def make_answer(**overrides) -> AssessmentAnswer:
    now = datetime.now(UTC)
    return AssessmentAnswer(
        id=overrides.get("id", uuid.uuid4()),
        session_id=overrides.get("session_id", uuid.uuid4()),
        question_number=overrides.get("question_number", 1),
        answer=overrides.get("answer", "OPTION_A"),
        created_at=now,
        updated_at=now,
    )


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
        status=overrides.get("status", RecordingStatus.PENDING),
        uploaded_at=overrides.get("uploaded_at"),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_assessment_session_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_assessment_session_service, None)


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


@pytest.fixture
def upload_authorized():
    """The recording-upload endpoint is authorized via
    resolve_recording_upload_org_id, not get_current_user (it accepts a
    recruiter JWT *or* a candidate's invitation token) — override that
    dependency directly rather than get_current_user."""
    app.dependency_overrides[resolve_recording_upload_org_id] = lambda: _ORG_ID
    yield _ORG_ID
    app.dependency_overrides.pop(resolve_recording_upload_org_id, None)


class TestCreateSession:
    _url = "/api/v1/assessment/session"

    async def test_creates_session(self, client_no_lifespan: AsyncClient, mock_service, recruiter: User):
        session = make_session()
        mock_service.create_or_resume = AsyncMock(return_value=session)

        res = await client_no_lifespan.post(
            self._url,
            json={"campaign_id": str(session.campaign_id), "candidate_id": str(session.candidate_id)},
        )

        assert res.status_code == 201
        body = res.json()
        assert body["id"] == str(session.id)
        assert body["status"] == "IN_PROGRESS"
        assert body["current_section"] == "APTITUDE"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(
            self._url, json={"campaign_id": str(uuid.uuid4()), "candidate_id": str(uuid.uuid4())}
        )
        assert res.status_code == 403
        mock_service.create_or_resume.assert_not_called()

    async def test_invalid_body_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(self._url, json={"campaign_id": "not-a-uuid"})
        assert res.status_code == 422
        mock_service.create_or_resume.assert_not_called()


class TestGetSession:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/{id_}"

    async def test_returns_session(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        session = make_session()
        mock_service.get_session = AsyncMock(return_value=session)

        res = await client_no_lifespan.get(self._url(session.id))

        assert res.status_code == 200
        assert res.json()["id"] == str(session.id)

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 403
        mock_service.get_session.assert_not_called()


class TestUpdateSession:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/{id_}"

    async def test_updates_progress(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        session = make_session(current_question=3)
        mock_service.update_progress = AsyncMock(return_value=session)

        res = await client_no_lifespan.patch(self._url(session.id), json={"current_question": 3})

        assert res.status_code == 200
        assert res.json()["current_question"] == 3

    async def test_out_of_range_question_number_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.patch(
            self._url(uuid.uuid4()), json={"current_question": 6}
        )
        assert res.status_code == 422
        mock_service.update_progress.assert_not_called()

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.patch(self._url(uuid.uuid4()), json={"current_question": 2})
        assert res.status_code == 403
        mock_service.update_progress.assert_not_called()


class TestSaveAnswer:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/{id_}/answers"

    async def test_saves_answer(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        answer = make_answer(question_number=2, answer="OPTION_B")
        mock_service.save_answer = AsyncMock(return_value=answer)

        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()), json={"question_number": 2, "answer": "OPTION_B"}
        )

        assert res.status_code == 201
        body = res.json()
        assert body["question_number"] == 2
        assert body["answer"] == "OPTION_B"

    async def test_out_of_range_question_number_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()), json={"question_number": 0, "answer": "x"}
        )
        assert res.status_code == 422
        mock_service.save_answer.assert_not_called()

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()), json={"question_number": 1, "answer": "x"}
        )
        assert res.status_code == 403
        mock_service.save_answer.assert_not_called()


class TestSaveRecording:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/{id_}/recordings"

    def _payload(self, **overrides) -> dict:
        payload = {
            "recording_type": "READ_ALOUD",
            "filename": "clip.webm",
            "mime_type": "audio/webm",
            "duration_seconds": 12.5,
            "file_size": 4096,
        }
        payload.update(overrides)
        return payload

    async def test_saves_recording_metadata(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        recording = make_recording()
        mock_service.save_recording = AsyncMock(return_value=recording)

        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=self._payload())

        assert res.status_code == 201
        body = res.json()
        assert body["recording_type"] == "READ_ALOUD"
        assert body["status"] == "PENDING"

    async def test_negative_duration_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()), json=self._payload(duration_seconds=-1)
        )
        assert res.status_code == 422
        mock_service.save_recording.assert_not_called()

    async def test_oversized_file_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()), json=self._payload(file_size=999_999_999)
        )
        assert res.status_code == 422
        mock_service.save_recording.assert_not_called()

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4()), json=self._payload())
        assert res.status_code == 403
        mock_service.save_recording.assert_not_called()


class TestUploadRecording:
    def _url(self, id_: uuid.UUID, recording_type: str = "READ_ALOUD") -> str:
        return f"/api/v1/assessment/session/{id_}/recordings/{recording_type}/upload"

    @pytest.fixture(autouse=True)
    def _no_celery(self):
        """Prevent real Celery dispatch in every test in this class."""
        with patch("app.api.v1.endpoints.assessment_sessions._enqueue_transcription") as m:
            self._mock_enqueue = m
            yield m

    async def test_uploads_recording_successfully(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        recording = make_recording(status=RecordingStatus.UPLOADED, uploaded_at=datetime.now(UTC))
        mock_service.upload_recording = AsyncMock(return_value=recording)

        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
            data={"duration_seconds": "12.5"},
        )

        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "UPLOADED"
        assert body["uploaded_at"] is not None

    async def test_dispatches_transcription_task_after_successful_upload(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        recording = make_recording(status=RecordingStatus.UPLOADED, uploaded_at=datetime.now(UTC))
        mock_service.upload_recording = AsyncMock(return_value=recording)

        await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
            data={"duration_seconds": "12.5"},
        )

        self._mock_enqueue.assert_called_once_with(str(recording.id))

    async def test_does_not_dispatch_when_upload_fails(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        from fastapi import HTTPException

        mock_service.upload_recording = AsyncMock(
            side_effect=HTTPException(status_code=422, detail="Unsupported audio type.")
        )

        await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.mp3", b"audio-bytes", "audio/mpeg")},
            data={"duration_seconds": "12.5"},
        )

        self._mock_enqueue.assert_not_called()

    async def test_no_recruiter_jwt_and_no_invitation_token_returns_401(
        self, client_no_lifespan: AsyncClient, mock_service
    ):
        """Neither the recruiter/admin JWT path nor the candidate invitation-
        token path is satisfied — no Authorization header, no
        X-Assessment-Token header — so resolve_recording_upload_org_id (the
        real dependency, not overridden in this test) must reject."""
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
            data={"duration_seconds": "12.5"},
        )
        assert res.status_code == 401
        mock_service.upload_recording.assert_not_called()

    async def test_missing_duration_seconds_returns_422(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
        )
        assert res.status_code == 422
        mock_service.upload_recording.assert_not_called()

    async def test_invalid_recording_type_path_param_returns_422(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        res = await client_no_lifespan.post(
            self._url(uuid.uuid4(), recording_type="BOGUS"),
            files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
            data={"duration_seconds": "12.5"},
        )
        assert res.status_code == 422
        mock_service.upload_recording.assert_not_called()

    async def test_service_422_propagates(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        from fastapi import HTTPException

        mock_service.upload_recording = AsyncMock(
            side_effect=HTTPException(status_code=422, detail="Unsupported audio type.")
        )

        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.mp3", b"audio-bytes", "audio/mpeg")},
            data={"duration_seconds": "12.5"},
        )
        assert res.status_code == 422

    async def test_service_404_propagates(
        self, client_no_lifespan: AsyncClient, mock_service, upload_authorized
    ):
        from fastapi import HTTPException

        mock_service.upload_recording = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Assessment session not found.")
        )

        res = await client_no_lifespan.post(
            self._url(uuid.uuid4()),
            files={"file": ("clip.webm", b"audio-bytes", "audio/webm")},
            data={"duration_seconds": "12.5"},
        )
        assert res.status_code == 404


class TestCompleteSession:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/assessment/session/{id_}/complete"

    async def test_completes_session(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        session = make_session(
            status=AssessmentSessionStatus.COMPLETED, completed_at=datetime.now(UTC)
        )
        mock_service.complete_session = AsyncMock(return_value=session)

        res = await client_no_lifespan.post(self._url(session.id))

        assert res.status_code == 200
        assert res.json()["status"] == "COMPLETED"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(self._url(uuid.uuid4()))
        assert res.status_code == 403
        mock_service.complete_session.assert_not_called()

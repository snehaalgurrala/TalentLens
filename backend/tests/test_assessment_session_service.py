"""Direct unit tests for AssessmentSessionService, using mocked repositories
rather than mocking the service itself — mirrors test_candidate_management_service.py.
"""
import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.models.assessment_recording import RecordingStatus, RecordingType
from app.models.assessment_session import (
    AssessmentSection,
    AssessmentSession,
    AssessmentSessionStatus,
)
from app.models.campaign import Campaign
from app.models.candidate import Candidate
from app.models.user import User, UserRole
from app.schemas.assessment_session import (
    AssessmentAnswerCreate,
    AssessmentRecordingCreate,
    AssessmentSessionCreate,
    AssessmentSessionProgressUpdate,
)
from app.services.assessment_session import AssessmentSessionService

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
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        campaign_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        current_section=AssessmentSection.APTITUDE,
        current_question=1,
        status=AssessmentSessionStatus.IN_PROGRESS,
        started_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentSession(**defaults)


def make_service(**repo_overrides) -> AssessmentSessionService:
    defaults = dict(
        session_repo=MagicMock(),
        answer_repo=MagicMock(),
        recording_repo=MagicMock(),
        campaign_repo=MagicMock(),
        candidate_repo=MagicMock(),
        storage=MagicMock(),
    )
    defaults.update(repo_overrides)
    return AssessmentSessionService(**defaults)


def make_upload_file(
    filename: str, content: bytes, content_type: str = "audio/webm"
) -> StarletteUploadFile:
    return StarletteUploadFile(
        filename=filename,
        file=io.BytesIO(content),
        size=len(content),
        headers={"content-type": content_type},
    )


# ── create_or_resume ─────────────────────────────────────────────────────────


class TestCreateOrResume:
    async def test_requires_org(self):
        service = make_service()
        user = make_user(org_id=None)

        with pytest.raises(HTTPException) as exc_info:
            await service.create_or_resume(
                AssessmentSessionCreate(campaign_id=uuid.uuid4(), candidate_id=uuid.uuid4()), user
            )
        assert exc_info.value.status_code == 422

    async def test_campaign_not_found(self):
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(campaign_repo=campaign_repo)
        user = make_user()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_or_resume(
                AssessmentSessionCreate(campaign_id=uuid.uuid4(), candidate_id=uuid.uuid4()), user
            )
        assert exc_info.value.status_code == 404

    async def test_candidate_not_found(self):
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=MagicMock(spec=Campaign))
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=None)
        service = make_service(campaign_repo=campaign_repo, candidate_repo=candidate_repo)
        user = make_user()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_or_resume(
                AssessmentSessionCreate(campaign_id=uuid.uuid4(), candidate_id=uuid.uuid4()), user
            )
        assert exc_info.value.status_code == 404

    async def test_resumes_existing_session_instead_of_creating(self):
        existing = make_session()
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=MagicMock(spec=Campaign))
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=MagicMock(spec=Candidate))
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=existing)
        session_repo.create = AsyncMock()
        service = make_service(
            campaign_repo=campaign_repo, candidate_repo=candidate_repo, session_repo=session_repo
        )
        user = make_user()

        result = await service.create_or_resume(
            AssessmentSessionCreate(campaign_id=existing.campaign_id, candidate_id=existing.candidate_id),
            user,
        )

        assert result is existing
        session_repo.create.assert_not_called()

    async def test_creates_new_session_when_none_exists(self):
        campaign_id = uuid.uuid4()
        candidate_id = uuid.uuid4()
        campaign_repo = MagicMock()
        campaign_repo.get_by_id = AsyncMock(return_value=MagicMock(spec=Campaign))
        candidate_repo = MagicMock()
        candidate_repo.get_by_id_and_org = AsyncMock(return_value=MagicMock(spec=Candidate))
        session_repo = MagicMock()
        session_repo.get_by_campaign_and_candidate = AsyncMock(return_value=None)
        created = make_session(campaign_id=campaign_id, candidate_id=candidate_id)
        session_repo.create = AsyncMock(return_value=created)
        service = make_service(
            campaign_repo=campaign_repo, candidate_repo=candidate_repo, session_repo=session_repo
        )
        user = make_user()

        result = await service.create_or_resume(
            AssessmentSessionCreate(campaign_id=campaign_id, candidate_id=candidate_id), user
        )

        assert result is created
        session_repo.create.assert_called_once()
        kwargs = session_repo.create.call_args.kwargs
        assert kwargs["org_id"] == _ORG_ID
        assert kwargs["campaign_id"] == campaign_id
        assert kwargs["candidate_id"] == candidate_id
        assert kwargs["current_section"] == AssessmentSection.APTITUDE
        assert kwargs["current_question"] == 1
        assert kwargs["status"] == AssessmentSessionStatus.IN_PROGRESS


# ── get_session ───────────────────────────────────────────────────────────────


class TestGetSession:
    async def test_not_found_raises_404(self):
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_session(uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_found_returns_session(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        service = make_service(session_repo=session_repo)

        result = await service.get_session(existing.id, make_user())
        assert result is existing


# ── update_progress ───────────────────────────────────────────────────────────


class TestUpdateProgress:
    async def test_rejects_update_on_completed_session(self):
        completed = make_session(status=AssessmentSessionStatus.COMPLETED)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=completed)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_progress(
                completed.id,
                AssessmentSessionProgressUpdate(current_question=2),
                make_user(),
            )
        assert exc_info.value.status_code == 422

    async def test_updates_progress_fields(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        session_repo.update = AsyncMock(return_value=existing)
        service = make_service(session_repo=session_repo)

        await service.update_progress(
            existing.id,
            AssessmentSessionProgressUpdate(current_question=3),
            make_user(),
        )

        session_repo.update.assert_called_once_with(existing, current_question=3)

    async def test_empty_update_skips_repo_call(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        session_repo.update = AsyncMock()
        service = make_service(session_repo=session_repo)

        result = await service.update_progress(
            existing.id, AssessmentSessionProgressUpdate(), make_user()
        )

        assert result is existing
        session_repo.update.assert_not_called()


# ── save_answer ───────────────────────────────────────────────────────────────


class TestSaveAnswer:
    async def test_rejects_answer_on_completed_session(self):
        completed = make_session(status=AssessmentSessionStatus.COMPLETED)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=completed)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.save_answer(
                completed.id, AssessmentAnswerCreate(question_number=1, answer="A"), make_user()
            )
        assert exc_info.value.status_code == 422

    async def test_upserts_answer(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        answer_repo = MagicMock()
        answer_repo.upsert = AsyncMock()
        service = make_service(session_repo=session_repo, answer_repo=answer_repo)

        await service.save_answer(
            existing.id, AssessmentAnswerCreate(question_number=2, answer="B"), make_user()
        )

        answer_repo.upsert.assert_called_once_with(existing.id, 2, "B")


# ── save_recording ────────────────────────────────────────────────────────────


class TestSaveRecording:
    async def test_rejects_recording_on_completed_session(self):
        completed = make_session(status=AssessmentSessionStatus.COMPLETED)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=completed)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.save_recording(
                completed.id,
                AssessmentRecordingCreate(
                    recording_type=RecordingType.READ_ALOUD,
                    filename="clip.webm",
                    mime_type="audio/webm",
                    duration_seconds=12.5,
                    file_size=1024,
                ),
                make_user(),
            )
        assert exc_info.value.status_code == 422

    async def test_upserts_recording_with_computed_storage_path(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        recording_repo = MagicMock()
        recording_repo.upsert = AsyncMock()
        service = make_service(session_repo=session_repo, recording_repo=recording_repo)

        await service.save_recording(
            existing.id,
            AssessmentRecordingCreate(
                recording_type=RecordingType.LISTEN_REPEAT,
                filename="clip.webm",
                mime_type="audio/webm",
                duration_seconds=8.0,
                file_size=2048,
            ),
            make_user(),
        )

        recording_repo.upsert.assert_called_once()
        args, kwargs = recording_repo.upsert.call_args
        assert args == (existing.id, RecordingType.LISTEN_REPEAT)
        assert kwargs["filename"] == "clip.webm"
        assert kwargs["mime_type"] == "audio/webm"
        assert kwargs["duration_seconds"] == 8.0
        assert kwargs["file_size"] == 2048
        assert kwargs["status"] == RecordingStatus.PENDING
        assert kwargs["storage_path"].startswith(f"assessment-recordings/{existing.id}/listen_repeat/")
        assert kwargs["storage_path"].endswith(".webm")


# ── upload_recording ──────────────────────────────────────────────────────────


class TestUploadRecording:
    async def test_session_not_found_returns_404(self):
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=None)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_recording(
                uuid.uuid4(),
                RecordingType.READ_ALOUD,
                make_upload_file("clip.webm", b"audio-bytes"),
                12.5,
                _ORG_ID,
            )
        assert exc_info.value.status_code == 404

    async def test_rejects_upload_on_completed_session(self):
        completed = make_session(status=AssessmentSessionStatus.COMPLETED)
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=completed)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_recording(
                completed.id,
                RecordingType.READ_ALOUD,
                make_upload_file("clip.webm", b"audio-bytes"),
                12.5,
                _ORG_ID,
            )
        assert exc_info.value.status_code == 422
        service.storage.save.assert_not_called()

    async def test_rejects_wrong_mime_type(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_recording(
                existing.id,
                RecordingType.READ_ALOUD,
                make_upload_file("clip.mp3", b"audio-bytes", content_type="audio/mpeg"),
                12.5,
                _ORG_ID,
            )
        assert exc_info.value.status_code == 422
        assert "audio/mpeg" in exc_info.value.detail
        service.storage.save.assert_not_called()

    async def test_strips_codecs_param_from_mime_type(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        recording_repo = MagicMock()
        recording_repo.upsert = AsyncMock()
        storage = MagicMock()
        storage.save = AsyncMock(return_value="ignored")
        service = make_service(session_repo=session_repo, recording_repo=recording_repo, storage=storage)

        await service.upload_recording(
            existing.id,
            RecordingType.READ_ALOUD,
            make_upload_file("clip.webm", b"audio-bytes", content_type="audio/webm;codecs=opus"),
            12.5,
            _ORG_ID,
        )

        storage.save.assert_called_once()
        kwargs = recording_repo.upsert.call_args.kwargs
        assert kwargs["mime_type"] == "audio/webm"

    async def test_rejects_empty_file(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        service = make_service(session_repo=session_repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_recording(
                existing.id,
                RecordingType.READ_ALOUD,
                make_upload_file("clip.webm", b""),
                12.5,
                _ORG_ID,
            )
        assert exc_info.value.status_code == 422
        service.storage.save.assert_not_called()

    async def test_rejects_oversized_file(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        service = make_service(session_repo=session_repo)
        oversized = b"0" * (10 * 1024 * 1024 + 1)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_recording(
                existing.id,
                RecordingType.READ_ALOUD,
                make_upload_file("clip.webm", oversized),
                12.5,
                _ORG_ID,
            )
        assert exc_info.value.status_code == 422
        assert "limit" in exc_info.value.detail
        service.storage.save.assert_not_called()

    async def test_successful_upload_calls_storage_and_upserts_uploaded_status(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        recording_repo = MagicMock()
        recording_repo.upsert = AsyncMock()
        storage = MagicMock()
        storage.save = AsyncMock(return_value="ignored")
        service = make_service(session_repo=session_repo, recording_repo=recording_repo, storage=storage)
        data = b"audio-bytes"

        await service.upload_recording(
            existing.id,
            RecordingType.READ_ALOUD,
            make_upload_file("clip.webm", data),
            12.5,
            _ORG_ID,
        )

        storage.save.assert_called_once()
        save_args = storage.save.call_args.args
        assert save_args[0].startswith(f"assessment-recordings/{existing.id}/read_aloud/")
        assert save_args[0].endswith(".webm")
        assert save_args[1] == data

        recording_repo.upsert.assert_called_once()
        args, kwargs = recording_repo.upsert.call_args
        assert args == (existing.id, RecordingType.READ_ALOUD)
        assert kwargs["mime_type"] == "audio/webm"
        assert kwargs["duration_seconds"] == 12.5
        assert kwargs["file_size"] == len(data)
        assert kwargs["status"] == RecordingStatus.UPLOADED
        assert isinstance(kwargs["uploaded_at"], datetime)

    async def test_storage_save_failure_raises_422_and_does_not_upsert(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        recording_repo = MagicMock()
        recording_repo.upsert = AsyncMock()
        storage = MagicMock()
        storage.save = AsyncMock(side_effect=OSError("disk full"))
        service = make_service(session_repo=session_repo, recording_repo=recording_repo, storage=storage)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_recording(
                existing.id,
                RecordingType.READ_ALOUD,
                make_upload_file("clip.webm", b"audio-bytes"),
                12.5,
                _ORG_ID,
            )
        assert exc_info.value.status_code == 422
        recording_repo.upsert.assert_not_called()


# ── complete_session ──────────────────────────────────────────────────────────


class TestCompleteSession:
    async def test_completes_in_progress_session(self):
        existing = make_session()
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=existing)
        completed = make_session(
            id=existing.id, status=AssessmentSessionStatus.COMPLETED, completed_at=datetime.now(UTC)
        )
        session_repo.update = AsyncMock(return_value=completed)
        service = make_service(session_repo=session_repo)

        result = await service.complete_session(existing.id, make_user())

        assert result.status == AssessmentSessionStatus.COMPLETED
        session_repo.update.assert_called_once()
        kwargs = session_repo.update.call_args.kwargs
        assert kwargs["status"] == AssessmentSessionStatus.COMPLETED
        assert kwargs["completed_at"] is not None

    async def test_completing_already_completed_session_is_idempotent(self):
        completed = make_session(status=AssessmentSessionStatus.COMPLETED, completed_at=datetime.now(UTC))
        session_repo = MagicMock()
        session_repo.get_by_id = AsyncMock(return_value=completed)
        session_repo.update = AsyncMock()
        service = make_service(session_repo=session_repo)

        result = await service.complete_session(completed.id, make_user())

        assert result is completed
        session_repo.update.assert_not_called()

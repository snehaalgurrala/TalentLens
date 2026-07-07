"""Direct unit tests for AssessmentTranscriptService, using a mocked
repository rather than mocking the service itself — mirrors
test_assessment_session_service.py.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.assessment_transcript import AssessmentTranscript, TranscriptStatus
from app.models.user import User, UserRole
from app.services.assessment_transcript import AssessmentTranscriptService

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
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        recording_id=uuid.uuid4(),
        status=TranscriptStatus.PENDING,
        transcript=None,
        language=None,
        model_name=None,
        processing_time_ms=None,
        segment_count=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentTranscript(**defaults)


def make_service(repo: MagicMock | None = None) -> AssessmentTranscriptService:
    return AssessmentTranscriptService(repo or MagicMock())


# ── create_pending ────────────────────────────────────────────────────────────


class TestCreatePending:
    async def test_creates_new_transcript_when_none_exists(self):
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=None)
        created = make_transcript()
        repo.create = AsyncMock(return_value=created)
        service = make_service(repo)

        result = await service.create_pending(created.recording_id, _ORG_ID)

        assert result is created
        repo.create.assert_called_once_with(
            created.recording_id, _ORG_ID, status=TranscriptStatus.PENDING
        )

    async def test_idempotent_returns_existing_without_creating(self):
        existing = make_transcript(status=TranscriptStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        repo.create = AsyncMock()
        service = make_service(repo)

        result = await service.create_pending(existing.recording_id, _ORG_ID)

        assert result is existing
        repo.create.assert_not_called()


# ── start_processing ──────────────────────────────────────────────────────────


class TestStartProcessing:
    async def test_marks_processing(self):
        existing = make_transcript()
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.start_processing(existing.recording_id)

        repo.update.assert_called_once_with(
            existing, status=TranscriptStatus.PROCESSING, error_message=None
        )

    async def test_missing_transcript_raises_value_error(self):
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(ValueError):
            await service.start_processing(uuid.uuid4())


# ── complete_processing ───────────────────────────────────────────────────────


class TestCompleteProcessing:
    async def test_persists_transcript_fields_and_marks_completed(self):
        existing = make_transcript(status=TranscriptStatus.PROCESSING)
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.complete_processing(
            existing.recording_id,
            transcript="hello world",
            language="en",
            model_name="base",
            processing_time_ms=1234,
            segment_count=2,
        )

        repo.update.assert_called_once_with(
            existing,
            status=TranscriptStatus.COMPLETED,
            transcript="hello world",
            language="en",
            model_name="base",
            processing_time_ms=1234,
            segment_count=2,
            error_message=None,
        )

    async def test_missing_transcript_raises_value_error(self):
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(ValueError):
            await service.complete_processing(
                uuid.uuid4(),
                transcript="x",
                language="en",
                model_name="base",
                processing_time_ms=1,
                segment_count=0,
            )


# ── fail_processing ───────────────────────────────────────────────────────────


class TestFailProcessing:
    async def test_marks_failed_with_error_message(self):
        existing = make_transcript(status=TranscriptStatus.PROCESSING)
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.fail_processing(existing.recording_id, "boom")

        repo.update.assert_called_once_with(
            existing, status=TranscriptStatus.FAILED, error_message="boom"
        )

    async def test_truncates_long_error_message(self):
        existing = make_transcript(status=TranscriptStatus.PROCESSING)
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.fail_processing(existing.recording_id, "x" * 2000)

        stored_msg = repo.update.call_args.kwargs["error_message"]
        assert len(stored_msg) == 1000

    async def test_missing_transcript_returns_none_without_raising(self):
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=None)
        repo.update = AsyncMock()
        service = make_service(repo)

        result = await service.fail_processing(uuid.uuid4(), "boom")

        assert result is None
        repo.update.assert_not_called()


# ── get_transcript ─────────────────────────────────────────────────────────────


class TestGetTranscript:
    async def test_requires_org(self):
        service = make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_transcript(uuid.uuid4(), make_user(org_id=None))
        assert exc_info.value.status_code == 422

    async def test_not_found_raises_404(self):
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_transcript(uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_other_org_transcript_raises_404(self):
        existing = make_transcript(organization_id=uuid.uuid4())
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        service = make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_transcript(existing.recording_id, make_user())
        assert exc_info.value.status_code == 404

    async def test_found_returns_transcript(self):
        existing = make_transcript()
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        service = make_service(repo)

        result = await service.get_transcript(existing.recording_id, make_user())
        assert result is existing


# ── retry_failed ───────────────────────────────────────────────────────────────


class TestRetryFailed:
    async def test_non_failed_transcript_rejected(self):
        existing = make_transcript(status=TranscriptStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        service = make_service(repo)
        dispatcher = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.retry_failed(existing.recording_id, make_user(), _dispatcher=dispatcher)
        assert exc_info.value.status_code == 422
        dispatcher.assert_not_called()

    async def test_resets_to_pending_and_dispatches(self):
        existing = make_transcript(status=TranscriptStatus.FAILED, error_message="boom")
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=existing)
        reset = make_transcript(
            id=existing.id,
            recording_id=existing.recording_id,
            status=TranscriptStatus.PENDING,
            error_message=None,
        )
        repo.update = AsyncMock(return_value=reset)
        service = make_service(repo)
        dispatcher = MagicMock()

        result = await service.retry_failed(existing.recording_id, make_user(), _dispatcher=dispatcher)

        assert result.status == TranscriptStatus.PENDING
        repo.update.assert_called_once_with(
            existing, status=TranscriptStatus.PENDING, error_message=None
        )
        dispatcher.assert_called_once_with(str(existing.recording_id))

    async def test_not_found_raises_404_before_dispatch(self):
        repo = MagicMock()
        repo.get_by_recording_id = AsyncMock(return_value=None)
        service = make_service(repo)
        dispatcher = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.retry_failed(uuid.uuid4(), make_user(), _dispatcher=dispatcher)
        assert exc_info.value.status_code == 404
        dispatcher.assert_not_called()

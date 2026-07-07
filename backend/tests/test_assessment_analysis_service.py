"""Direct unit tests for AssessmentAnalysisService, using a mocked repository
rather than mocking the service itself — mirrors
test_assessment_transcript_service.py.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.assessment_analysis import AnalysisStatus, AnalysisType, AssessmentAnalysis
from app.models.user import User, UserRole
from app.services.assessment_analysis import AssessmentAnalysisService

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


def make_analysis(**overrides) -> AssessmentAnalysis:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        transcript_id=uuid.uuid4(),
        analysis_type=AnalysisType.READ_ALOUD,
        status=AnalysisStatus.PENDING,
        overall_score=None,
        word_accuracy=None,
        correct_words=None,
        missing_words=None,
        extra_words=None,
        substituted_words=None,
        total_words=None,
        reading_speed_wpm=None,
        completion_percentage=None,
        analysis_json=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return AssessmentAnalysis(**defaults)


def make_service(repo: MagicMock | None = None) -> AssessmentAnalysisService:
    return AssessmentAnalysisService(repo or MagicMock())


# ── create_pending ────────────────────────────────────────────────────────────


class TestCreatePending:
    async def test_creates_new_analysis_when_none_exists(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        created = make_analysis()
        repo.create = AsyncMock(return_value=created)
        service = make_service(repo)

        result = await service.create_pending(created.transcript_id, _ORG_ID)

        assert result is created
        repo.create.assert_called_once_with(
            created.transcript_id,
            _ORG_ID,
            analysis_type=AnalysisType.READ_ALOUD,
            status=AnalysisStatus.PENDING,
        )

    async def test_idempotent_returns_existing_without_creating(self):
        existing = make_analysis(status=AnalysisStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        repo.create = AsyncMock()
        service = make_service(repo)

        result = await service.create_pending(existing.transcript_id, _ORG_ID)

        assert result is existing
        repo.create.assert_not_called()

    async def test_creates_listen_repeat_analysis_when_requested(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        created = make_analysis(analysis_type=AnalysisType.LISTEN_REPEAT)
        repo.create = AsyncMock(return_value=created)
        service = make_service(repo)

        result = await service.create_pending(
            created.transcript_id, _ORG_ID, analysis_type=AnalysisType.LISTEN_REPEAT
        )

        assert result is created
        repo.create.assert_called_once_with(
            created.transcript_id,
            _ORG_ID,
            analysis_type=AnalysisType.LISTEN_REPEAT,
            status=AnalysisStatus.PENDING,
        )


# ── complete_processing ───────────────────────────────────────────────────────


class TestCompleteProcessing:
    async def test_persists_metrics_and_marks_completed(self):
        existing = make_analysis(status=AnalysisStatus.PENDING)
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.complete_processing(
            existing.transcript_id,
            overall_score=91.5,
            word_accuracy=95.0,
            correct_words=19,
            missing_words=1,
            extra_words=0,
            substituted_words=0,
            total_words=20,
            reading_speed_wpm=120.0,
            completion_percentage=95.0,
            analysis_json={"correct_words": []},
        )

        repo.update.assert_called_once_with(
            existing,
            status=AnalysisStatus.COMPLETED,
            overall_score=91.5,
            word_accuracy=95.0,
            correct_words=19,
            missing_words=1,
            extra_words=0,
            substituted_words=0,
            total_words=20,
            reading_speed_wpm=120.0,
            completion_percentage=95.0,
            analysis_json={"correct_words": []},
            error_message=None,
        )

    async def test_missing_analysis_raises_value_error(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(ValueError):
            await service.complete_processing(
                uuid.uuid4(),
                overall_score=1.0,
                word_accuracy=1.0,
                correct_words=1,
                missing_words=0,
                extra_words=0,
                substituted_words=0,
                total_words=1,
                reading_speed_wpm=1.0,
                completion_percentage=1.0,
                analysis_json={},
            )


# ── complete_listen_repeat_processing ─────────────────────────────────────────


class TestCompleteListenRepeatProcessing:
    async def test_persists_metrics_and_marks_completed(self):
        existing = make_analysis(
            analysis_type=AnalysisType.LISTEN_REPEAT, status=AnalysisStatus.PENDING
        )
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.complete_listen_repeat_processing(
            existing.transcript_id,
            overall_score=82.5,
            semantic_similarity=90.0,
            keyword_coverage=75.0,
            completion_percentage=80.0,
            analysis_json={"matched_keywords": []},
        )

        repo.update.assert_called_once_with(
            existing,
            status=AnalysisStatus.COMPLETED,
            overall_score=82.5,
            semantic_similarity=90.0,
            keyword_coverage=75.0,
            completion_percentage=80.0,
            analysis_json={"matched_keywords": []},
            error_message=None,
        )

    async def test_missing_analysis_raises_value_error(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(ValueError):
            await service.complete_listen_repeat_processing(
                uuid.uuid4(),
                overall_score=1.0,
                semantic_similarity=1.0,
                keyword_coverage=1.0,
                completion_percentage=1.0,
                analysis_json={},
            )


# ── fail_processing ───────────────────────────────────────────────────────────


class TestFailProcessing:
    async def test_marks_failed_with_error_message(self):
        existing = make_analysis(status=AnalysisStatus.PENDING)
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.fail_processing(existing.transcript_id, "boom")

        repo.update.assert_called_once_with(
            existing, status=AnalysisStatus.FAILED, error_message="boom"
        )

    async def test_truncates_long_error_message(self):
        existing = make_analysis(status=AnalysisStatus.PENDING)
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.fail_processing(existing.transcript_id, "x" * 2000)

        stored_msg = repo.update.call_args.kwargs["error_message"]
        assert len(stored_msg) == 1000

    async def test_missing_analysis_returns_none_without_raising(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        repo.update = AsyncMock()
        service = make_service(repo)

        result = await service.fail_processing(uuid.uuid4(), "boom")

        assert result is None
        repo.update.assert_not_called()


# ── get_analysis ───────────────────────────────────────────────────────────────


class TestGetAnalysis:
    async def test_requires_org(self):
        service = make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_analysis(uuid.uuid4(), make_user(org_id=None))
        assert exc_info.value.status_code == 422

    async def test_not_found_raises_404(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_analysis(uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_other_org_analysis_raises_404(self):
        existing = make_analysis(organization_id=uuid.uuid4())
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        service = make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_analysis(existing.transcript_id, make_user())
        assert exc_info.value.status_code == 404

    async def test_found_returns_analysis(self):
        existing = make_analysis()
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        service = make_service(repo)

        result = await service.get_analysis(existing.transcript_id, make_user())
        assert result is existing


# ── retry_failed ───────────────────────────────────────────────────────────────


class TestRetryFailed:
    async def test_non_failed_analysis_rejected(self):
        existing = make_analysis(status=AnalysisStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        service = make_service(repo)
        dispatcher = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.retry_failed(
                existing.transcript_id, make_user(), 9.5, _dispatcher=dispatcher
            )
        assert exc_info.value.status_code == 422
        dispatcher.assert_not_called()

    async def test_resets_to_pending_and_dispatches(self):
        existing = make_analysis(status=AnalysisStatus.FAILED, error_message="boom")
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=existing)
        reset = make_analysis(
            id=existing.id,
            transcript_id=existing.transcript_id,
            status=AnalysisStatus.PENDING,
            error_message=None,
        )
        repo.update = AsyncMock(return_value=reset)
        service = make_service(repo)
        dispatcher = MagicMock()

        result = await service.retry_failed(
            existing.transcript_id, make_user(), 9.5, _dispatcher=dispatcher
        )

        assert result.status == AnalysisStatus.PENDING
        repo.update.assert_called_once_with(
            existing, status=AnalysisStatus.PENDING, error_message=None
        )
        dispatcher.assert_called_once_with(str(existing.transcript_id), 9.5)

    async def test_not_found_raises_404_before_dispatch(self):
        repo = MagicMock()
        repo.get_by_transcript_id = AsyncMock(return_value=None)
        service = make_service(repo)
        dispatcher = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.retry_failed(uuid.uuid4(), make_user(), 9.5, _dispatcher=dispatcher)
        assert exc_info.value.status_code == 404
        dispatcher.assert_not_called()

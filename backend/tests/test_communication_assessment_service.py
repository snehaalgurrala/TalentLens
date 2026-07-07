"""Direct unit tests for CommunicationAssessmentService, using a mocked
repository rather than mocking the service itself — mirrors
test_assessment_analysis_service.py.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.communication_assessment import (
    CommunicationAssessment,
    CommunicationAssessmentStatus,
)
from app.models.user import User, UserRole
from app.services.communication_assessment import CommunicationAssessmentService

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
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        assessment_session_id=uuid.uuid4(),
        status=CommunicationAssessmentStatus.PENDING,
        overall_score=None,
        reading_score=None,
        listening_score=None,
        confidence_score=None,
        strengths_json=None,
        improvements_json=None,
        summary_json=None,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return CommunicationAssessment(**defaults)


def make_service(repo: MagicMock | None = None) -> CommunicationAssessmentService:
    return CommunicationAssessmentService(repo or MagicMock())


# ── create_pending ────────────────────────────────────────────────────────────


class TestCreatePending:
    async def test_creates_new_assessment_when_none_exists(self):
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=None)
        created = make_assessment()
        repo.create = AsyncMock(return_value=created)
        service = make_service(repo)

        result = await service.create_pending(created.assessment_session_id, _ORG_ID)

        assert result is created
        repo.create.assert_called_once_with(
            created.assessment_session_id,
            _ORG_ID,
            status=CommunicationAssessmentStatus.PENDING,
        )

    async def test_idempotent_returns_existing_without_creating(self):
        existing = make_assessment(status=CommunicationAssessmentStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        repo.create = AsyncMock()
        service = make_service(repo)

        result = await service.create_pending(existing.assessment_session_id, _ORG_ID)

        assert result is existing
        repo.create.assert_not_called()


# ── complete_processing ───────────────────────────────────────────────────────


class TestCompleteProcessing:
    async def test_persists_scores_and_marks_completed(self):
        existing = make_assessment(status=CommunicationAssessmentStatus.PENDING)
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.complete_processing(
            existing.assessment_session_id,
            overall_score=85.0,
            reading_score=90.0,
            listening_score=80.0,
            confidence_score=88.0,
            strengths_json=["Reads clearly and accurately"],
            improvements_json=[],
            summary_json={"overview": "Great job."},
        )

        repo.update.assert_called_once_with(
            existing,
            status=CommunicationAssessmentStatus.COMPLETED,
            overall_score=85.0,
            reading_score=90.0,
            listening_score=80.0,
            confidence_score=88.0,
            strengths_json=["Reads clearly and accurately"],
            improvements_json=[],
            summary_json={"overview": "Great job."},
            error_message=None,
        )

    async def test_missing_assessment_raises_value_error(self):
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(ValueError):
            await service.complete_processing(
                uuid.uuid4(),
                overall_score=1.0,
                reading_score=1.0,
                listening_score=1.0,
                confidence_score=1.0,
                strengths_json=[],
                improvements_json=[],
                summary_json={},
            )


# ── fail_processing ───────────────────────────────────────────────────────────


class TestFailProcessing:
    async def test_marks_failed_with_error_message(self):
        existing = make_assessment(status=CommunicationAssessmentStatus.PENDING)
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.fail_processing(existing.assessment_session_id, "boom")

        repo.update.assert_called_once_with(
            existing, status=CommunicationAssessmentStatus.FAILED, error_message="boom"
        )

    async def test_truncates_long_error_message(self):
        existing = make_assessment(status=CommunicationAssessmentStatus.PENDING)
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        repo.update = AsyncMock(return_value=existing)
        service = make_service(repo)

        await service.fail_processing(existing.assessment_session_id, "x" * 2000)

        stored_msg = repo.update.call_args.kwargs["error_message"]
        assert len(stored_msg) == 1000

    async def test_missing_assessment_returns_none_without_raising(self):
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=None)
        repo.update = AsyncMock()
        service = make_service(repo)

        result = await service.fail_processing(uuid.uuid4(), "boom")

        assert result is None
        repo.update.assert_not_called()


# ── get_assessment ─────────────────────────────────────────────────────────────


class TestGetAssessment:
    async def test_requires_org(self):
        service = make_service()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_assessment(uuid.uuid4(), make_user(org_id=None))
        assert exc_info.value.status_code == 422

    async def test_not_found_raises_404(self):
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=None)
        service = make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_assessment(uuid.uuid4(), make_user())
        assert exc_info.value.status_code == 404

    async def test_other_org_assessment_raises_404(self):
        existing = make_assessment(organization_id=uuid.uuid4())
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        service = make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_assessment(existing.assessment_session_id, make_user())
        assert exc_info.value.status_code == 404

    async def test_found_returns_assessment(self):
        existing = make_assessment()
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        service = make_service(repo)

        result = await service.get_assessment(existing.assessment_session_id, make_user())
        assert result is existing


# ── retry_failed ───────────────────────────────────────────────────────────────


class TestRetryFailed:
    async def test_non_failed_assessment_rejected(self):
        existing = make_assessment(status=CommunicationAssessmentStatus.COMPLETED)
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        service = make_service(repo)
        dispatcher = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.retry_failed(
                existing.assessment_session_id, make_user(), _dispatcher=dispatcher
            )
        assert exc_info.value.status_code == 422
        dispatcher.assert_not_called()

    async def test_resets_to_pending_and_dispatches(self):
        existing = make_assessment(
            status=CommunicationAssessmentStatus.FAILED, error_message="boom"
        )
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=existing)
        reset = make_assessment(
            id=existing.id,
            assessment_session_id=existing.assessment_session_id,
            status=CommunicationAssessmentStatus.PENDING,
            error_message=None,
        )
        repo.update = AsyncMock(return_value=reset)
        service = make_service(repo)
        dispatcher = MagicMock()

        result = await service.retry_failed(
            existing.assessment_session_id, make_user(), _dispatcher=dispatcher
        )

        assert result.status == CommunicationAssessmentStatus.PENDING
        repo.update.assert_called_once_with(
            existing, status=CommunicationAssessmentStatus.PENDING, error_message=None
        )
        dispatcher.assert_called_once_with(str(existing.assessment_session_id))

    async def test_not_found_raises_404_before_dispatch(self):
        repo = MagicMock()
        repo.get_by_session_id = AsyncMock(return_value=None)
        service = make_service(repo)
        dispatcher = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.retry_failed(uuid.uuid4(), make_user(), _dispatcher=dispatcher)
        assert exc_info.value.status_code == 404
        dispatcher.assert_not_called()

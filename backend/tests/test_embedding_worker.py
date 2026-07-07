"""
Unit tests for app.workers.embedding_worker.

No real database, no real sentence-transformers model load. LocalEmbeddingService
itself is mocked out (it already has its own tests); these tests only verify
the worker's session lifecycle, commit-on-both-success-and-failure behavior,
and retry classification.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.workers.embedding_worker import (
    _generate_job_description_embedding_task,
    _generate_resume_embedding_task,
    _run_generate_job_description_embedding,
    _run_generate_resume_embedding,
)


def _make_session_factory(session_mock: AsyncMock) -> MagicMock:
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


# ── _run_generate_resume_embedding ─────────────────────────────────────────────


class TestRunGenerateResumeEmbedding:
    async def test_success_commits_once(self):
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        mock_service = MagicMock()
        mock_service.embed_resume = AsyncMock()

        with patch(
            "app.workers.embedding_worker.LocalEmbeddingService", return_value=mock_service
        ):
            await _run_generate_resume_embedding(
                str(uuid.uuid4()), _session_factory=session_factory
            )

        mock_service.embed_resume.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_failure_still_commits_before_propagating(self):
        """LocalEmbeddingService marks the row FAILED internally before
        re-raising; that status change must be committed, not lost."""
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        mock_service = MagicMock()
        mock_service.embed_resume = AsyncMock(side_effect=RuntimeError("model load failed"))

        with patch(
            "app.workers.embedding_worker.LocalEmbeddingService", return_value=mock_service
        ):
            with pytest.raises(RuntimeError):
                await _run_generate_resume_embedding(
                    str(uuid.uuid4()), _session_factory=session_factory
                )

        session.commit.assert_awaited_once()

    async def test_missing_row_raises_value_error(self):
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        mock_service = MagicMock()
        mock_service.embed_resume = AsyncMock(side_effect=ValueError("not found"))

        with patch(
            "app.workers.embedding_worker.LocalEmbeddingService", return_value=mock_service
        ):
            with pytest.raises(ValueError):
                await _run_generate_resume_embedding(
                    str(uuid.uuid4()), _session_factory=session_factory
                )

        session.commit.assert_awaited_once()


# ── _run_generate_job_description_embedding ────────────────────────────────────


class TestRunGenerateJobDescriptionEmbedding:
    async def test_success_commits_once(self):
        session = AsyncMock()
        session_factory = _make_session_factory(session)
        mock_service = MagicMock()
        mock_service.embed_job_description = AsyncMock()

        with patch(
            "app.workers.embedding_worker.LocalEmbeddingService", return_value=mock_service
        ):
            await _run_generate_job_description_embedding(
                str(uuid.uuid4()), _session_factory=session_factory
            )

        mock_service.embed_job_description.assert_awaited_once()
        session.commit.assert_awaited_once()


# ── Celery task retry classification ───────────────────────────────────────────


class TestResumeEmbeddingTaskClassification:
    def test_value_error_raises_without_retry(self):
        mock_self = MagicMock()
        mock_self.request.retries = 0

        with patch(
            "app.workers.embedding_worker.run_task",
            MagicMock(side_effect=ValueError("no structured_json")),
        ):
            with pytest.raises(ValueError):
                _generate_resume_embedding_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()

    def test_unexpected_exception_triggers_retry_with_backoff(self):
        mock_self = MagicMock()
        mock_self.request.retries = 1
        mock_self.retry.side_effect = Retry()

        with patch(
            "app.workers.embedding_worker.run_task",
            MagicMock(side_effect=RuntimeError("boom")),
        ):
            with pytest.raises(Retry):
                _generate_resume_embedding_task(mock_self, "some-uuid")

        _, kwargs = mock_self.retry.call_args
        assert kwargs["countdown"] == 60  # 30 * 2^1


class TestJobDescriptionEmbeddingTaskClassification:
    def test_value_error_raises_without_retry(self):
        mock_self = MagicMock()
        mock_self.request.retries = 0

        with patch(
            "app.workers.embedding_worker.run_task",
            MagicMock(side_effect=ValueError("no structured_json")),
        ):
            with pytest.raises(ValueError):
                _generate_job_description_embedding_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()

    def test_unexpected_exception_triggers_retry_with_backoff(self):
        mock_self = MagicMock()
        mock_self.request.retries = 2
        mock_self.retry.side_effect = Retry()

        with patch(
            "app.workers.embedding_worker.run_task",
            MagicMock(side_effect=RuntimeError("boom")),
        ):
            with pytest.raises(Retry):
                _generate_job_description_embedding_task(mock_self, "some-uuid")

        _, kwargs = mock_self.retry.call_args
        assert kwargs["countdown"] == 120  # 30 * 2^2

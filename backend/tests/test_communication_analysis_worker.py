"""
Unit tests for app.workers.communication_analysis.

No real database, no real Redis. All dependencies are injected via the
_session_factory / _analysis_service keyword arguments on
_run_analyze_read_aloud and _mark_failed, so no module-level patching of
AsyncSessionLocal is needed — mirrors test_speech_transcription_worker.py.

Async tests run automatically because asyncio_mode = "auto" in pyproject.toml.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.ai.communication.exceptions import InvalidDurationError
from app.ai.communication.schemas import (
    ListenRepeatAnalysisResult,
    ListenRepeatMetrics,
    ReadAloudAnalysisResult,
    ReadAloudMetrics,
    WordComparisonResult,
)
from app.core.config import settings
from app.models.assessment_analysis import AnalysisStatus, AnalysisType
from app.models.assessment_transcript import TranscriptStatus
from app.workers.communication_analysis import (
    _analyze_listen_repeat_task,
    _analyze_read_aloud_task,
    _mark_failed,
    _run_analyze_listen_repeat,
    _run_analyze_read_aloud,
)

# ── Shared fixture helpers ────────────────────────────────────────────────────


def _make_transcript(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        status=TranscriptStatus.COMPLETED,
        transcript="the quick brown fox",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_analysis(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        transcript_id=overrides.get("transcript_id", uuid.uuid4()),
        organization_id=uuid.uuid4(),
        status=AnalysisStatus.PENDING,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_analysis_result(**overrides) -> ReadAloudAnalysisResult:
    defaults = dict(
        comparison=WordComparisonResult(
            correct_words=["the", "quick", "brown", "fox"],
            missing_words=[],
            extra_words=[],
            substitutions=[],
        ),
        metrics=ReadAloudMetrics(
            total_words=4,
            correct_words=4,
            missing_words=0,
            extra_words=0,
            substituted_words=0,
            word_accuracy=100.0,
            completion_percentage=100.0,
            reading_speed_wpm=60.0,
            overall_score=100.0,
        ),
    )
    defaults.update(overrides)
    return ReadAloudAnalysisResult(**defaults)


def _make_listen_repeat_result(**overrides) -> ListenRepeatAnalysisResult:
    defaults = dict(
        metrics=ListenRepeatMetrics(
            reference_word_count=4,
            hypothesis_word_count=4,
            semantic_similarity=95.0,
            keyword_coverage=100.0,
            completion_percentage=100.0,
            overall_score=97.0,
            matched_keywords=["quick", "brown", "fox"],
            missing_keywords=[],
        )
    )
    defaults.update(overrides)
    return ListenRepeatAnalysisResult(**defaults)


def _make_session_factory(session_mock: AsyncMock) -> MagicMock:
    """Wrap a mock session in an async context manager returned by a callable."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


# ── _run_analyze_read_aloud — happy path ─────────────────────────────────────


class TestRunAnalyzeReadAloudHappyPath:
    async def test_analyzes_and_marks_completed(self):
        transcript = _make_transcript()
        analysis = _make_analysis(transcript_id=transcript.id, status=AnalysisStatus.PENDING)
        result = _make_analysis_result()

        session = AsyncMock()
        session.get = AsyncMock(return_value=transcript)
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        analysis_service = MagicMock()
        analysis_service.analyze = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_analysis.AssessmentAnalysisRepository"),
            patch(
                "app.workers.communication_analysis.AssessmentAnalysisService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=analysis)
            mock_service.complete_processing = AsyncMock(return_value=analysis)

            await _run_analyze_read_aloud(
                str(transcript.id),
                9.5,
                _session_factory=session_factory,
                _analysis_service=analysis_service,
            )

            mock_service.create_pending.assert_awaited_once_with(
                transcript.id, transcript.organization_id
            )
            analysis_service.analyze.assert_called_once_with(
                settings.READ_ALOUD_REFERENCE_SENTENCE, transcript.transcript, 9.5
            )
            mock_service.complete_processing.assert_awaited_once_with(
                transcript.id,
                overall_score=100.0,
                word_accuracy=100.0,
                correct_words=4,
                missing_words=0,
                extra_words=0,
                substituted_words=0,
                total_words=4,
                reading_speed_wpm=60.0,
                completion_percentage=100.0,
                analysis_json=result.comparison.model_dump(mode="json"),
            )
        assert session.commit.await_count == 2

    async def test_transcript_not_found_returns_silently(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session_factory = _make_session_factory(session)

        await _run_analyze_read_aloud(str(uuid.uuid4()), 9.5, _session_factory=session_factory)

        session.commit.assert_not_awaited()

    async def test_transcript_not_completed_returns_silently(self):
        transcript = _make_transcript(status=TranscriptStatus.PROCESSING)
        session = AsyncMock()
        session.get = AsyncMock(return_value=transcript)
        session_factory = _make_session_factory(session)

        await _run_analyze_read_aloud(str(transcript.id), 9.5, _session_factory=session_factory)

        session.commit.assert_not_awaited()

    async def test_already_completed_analysis_skips_all_work(self):
        transcript = _make_transcript()
        analysis = _make_analysis(transcript_id=transcript.id, status=AnalysisStatus.COMPLETED)

        session = AsyncMock()
        session.get = AsyncMock(return_value=transcript)
        session_factory = _make_session_factory(session)
        analysis_service = MagicMock()

        with (
            patch("app.workers.communication_analysis.AssessmentAnalysisRepository"),
            patch(
                "app.workers.communication_analysis.AssessmentAnalysisService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=analysis)

            await _run_analyze_read_aloud(
                str(transcript.id),
                9.5,
                _session_factory=session_factory,
                _analysis_service=analysis_service,
            )

        analysis_service.analyze.assert_not_called()


# ── _run_analyze_listen_repeat — happy path ──────────────────────────────────


class TestRunAnalyzeListenRepeatHappyPath:
    async def test_analyzes_and_marks_completed(self):
        transcript = _make_transcript()
        analysis = _make_analysis(transcript_id=transcript.id, status=AnalysisStatus.PENDING)
        result = _make_listen_repeat_result()

        session = AsyncMock()
        session.get = AsyncMock(return_value=transcript)
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        analysis_service = MagicMock()
        analysis_service.analyze = MagicMock(return_value=result)

        with (
            patch("app.workers.communication_analysis.AssessmentAnalysisRepository"),
            patch(
                "app.workers.communication_analysis.AssessmentAnalysisService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=analysis)
            mock_service.complete_listen_repeat_processing = AsyncMock(return_value=analysis)

            await _run_analyze_listen_repeat(
                str(transcript.id),
                9.5,
                _session_factory=session_factory,
                _analysis_service=analysis_service,
            )

            mock_service.create_pending.assert_awaited_once_with(
                transcript.id,
                transcript.organization_id,
                analysis_type=AnalysisType.LISTEN_REPEAT,
            )
            analysis_service.analyze.assert_called_once_with(
                settings.LISTEN_REPEAT_REFERENCE_SENTENCE, transcript.transcript, 9.5
            )
            mock_service.complete_listen_repeat_processing.assert_awaited_once_with(
                transcript.id,
                overall_score=97.0,
                semantic_similarity=95.0,
                keyword_coverage=100.0,
                completion_percentage=100.0,
                analysis_json=result.metrics.model_dump(mode="json"),
            )
        assert session.commit.await_count == 2

    async def test_transcript_not_found_returns_silently(self):
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session_factory = _make_session_factory(session)

        await _run_analyze_listen_repeat(str(uuid.uuid4()), 9.5, _session_factory=session_factory)

        session.commit.assert_not_awaited()

    async def test_transcript_not_completed_returns_silently(self):
        transcript = _make_transcript(status=TranscriptStatus.PROCESSING)
        session = AsyncMock()
        session.get = AsyncMock(return_value=transcript)
        session_factory = _make_session_factory(session)

        await _run_analyze_listen_repeat(
            str(transcript.id), 9.5, _session_factory=session_factory
        )

        session.commit.assert_not_awaited()

    async def test_already_completed_analysis_skips_all_work(self):
        transcript = _make_transcript()
        analysis = _make_analysis(transcript_id=transcript.id, status=AnalysisStatus.COMPLETED)

        session = AsyncMock()
        session.get = AsyncMock(return_value=transcript)
        session_factory = _make_session_factory(session)
        analysis_service = MagicMock()

        with (
            patch("app.workers.communication_analysis.AssessmentAnalysisRepository"),
            patch(
                "app.workers.communication_analysis.AssessmentAnalysisService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=analysis)

            await _run_analyze_listen_repeat(
                str(transcript.id),
                9.5,
                _session_factory=session_factory,
                _analysis_service=analysis_service,
            )

        analysis_service.analyze.assert_not_called()


# ── _mark_failed ──────────────────────────────────────────────────────────────


class TestMarkFailed:
    async def test_sets_status_and_error_message(self):
        transcript_id = uuid.uuid4()
        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with (
            patch("app.workers.communication_analysis.AssessmentAnalysisRepository"),
            patch(
                "app.workers.communication_analysis.AssessmentAnalysisService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.fail_processing = AsyncMock()

            await _mark_failed(
                str(transcript_id), "something went wrong", _session_factory=session_factory
            )

            mock_service.fail_processing.assert_awaited_once_with(
                transcript_id, "something went wrong"
            )
        session.commit.assert_awaited_once()

    async def test_db_error_is_swallowed(self):
        session_factory = MagicMock(side_effect=RuntimeError("DB is down"))

        await _mark_failed(str(uuid.uuid4()), "original error", _session_factory=session_factory)


# ── _analyze_read_aloud_task (Celery error classification) ───────────────────


class TestCeleryTaskErrorClassification:
    def _make_self(self, retries: int = 0) -> MagicMock:
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.retry.side_effect = Retry()
        return mock_self

    def test_invalid_duration_error_raises_without_retry(self):
        mock_self = self._make_self()
        exc = InvalidDurationError("Recording duration must be a non-negative number")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(InvalidDurationError):
                _analyze_read_aloud_task(mock_self, "some-uuid", 9.5)

        mock_self.retry.assert_not_called()

    def test_unexpected_exception_triggers_retry_with_backoff(self):
        mock_self = self._make_self(retries=0)
        exc = RuntimeError("db hiccup")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _analyze_read_aloud_task(mock_self, "some-uuid", 9.5)

        mock_self.retry.assert_called_once()
        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 30  # 30 * 2^0

    def test_retry_backoff_doubles_each_attempt(self):
        mock_self = self._make_self(retries=2)  # third attempt
        exc = RuntimeError("something broke")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _analyze_read_aloud_task(mock_self, "some-uuid", 9.5)

        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 120  # 30 * 2^2

    def test_happy_path_completes_without_retry(self):
        mock_self = self._make_self()

        with patch("asyncio.run", lambda coro: None):
            _analyze_read_aloud_task(mock_self, "some-uuid", 9.5)

        mock_self.retry.assert_not_called()


# ── _analyze_listen_repeat_task (Celery error classification) ───────────────


class TestListenRepeatCeleryTaskErrorClassification:
    def _make_self(self, retries: int = 0) -> MagicMock:
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.retry.side_effect = Retry()
        return mock_self

    def test_invalid_duration_error_raises_without_retry(self):
        mock_self = self._make_self()
        exc = InvalidDurationError("Recording duration must be a non-negative number")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(InvalidDurationError):
                _analyze_listen_repeat_task(mock_self, "some-uuid", 9.5)

        mock_self.retry.assert_not_called()

    def test_unexpected_exception_triggers_retry_with_backoff(self):
        mock_self = self._make_self(retries=0)
        exc = RuntimeError("db hiccup")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _analyze_listen_repeat_task(mock_self, "some-uuid", 9.5)

        mock_self.retry.assert_called_once()
        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 30  # 30 * 2^0

    def test_happy_path_completes_without_retry(self):
        mock_self = self._make_self()

        with patch("asyncio.run", lambda coro: None):
            _analyze_listen_repeat_task(mock_self, "some-uuid", 9.5)

        mock_self.retry.assert_not_called()

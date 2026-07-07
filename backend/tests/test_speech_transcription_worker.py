"""
Unit tests for app.workers.speech_transcription.

No real database, no real Redis, no real Whisper model. All dependencies are
injected via the _session_factory / _speech_service / _storage keyword
arguments on _run_transcribe_recording and _mark_failed, so no module-level
patching of AsyncSessionLocal is needed — mirrors test_job_description_parser.py.

Async tests run automatically because asyncio_mode = "auto" in pyproject.toml.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.ai.speech.exceptions import AudioValidationError, TranscriptionError
from app.ai.speech.schemas import TranscriptionResult
from app.models.assessment_recording import RecordingType
from app.models.assessment_transcript import TranscriptStatus
from app.workers.speech_transcription import (
    _mark_failed,
    _run_transcribe_recording,
    _transcribe_recording_task,
)

# ── Shared fixture helpers ────────────────────────────────────────────────────


def _make_recording(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        storage_path="assessment-recordings/x/read_aloud/y.webm",
        mime_type="audio/webm",
        filename="clip.webm",
        recording_type=RecordingType.READ_ALOUD,
        duration_seconds=9.5,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_transcript(**overrides) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        recording_id=overrides.get("recording_id", uuid.uuid4()),
        organization_id=uuid.uuid4(),
        status=TranscriptStatus.PENDING,
        error_message=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_transcription_result(**overrides) -> TranscriptionResult:
    defaults = dict(
        transcript="hello world",
        language="en",
        duration_seconds=3.0,
        processing_time_seconds=1.5,
        model_name="base",
        confidence=0.9,
        segments=[],
    )
    defaults.update(overrides)
    return TranscriptionResult(**defaults)


def _make_session_factory(session_mock: AsyncMock) -> MagicMock:
    """Wrap a mock session in an async context manager returned by a callable."""
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=cm)


def _make_execute_result(row):
    result = MagicMock()
    result.first.return_value = row
    return result


# ── _run_transcribe_recording — happy path ───────────────────────────────────


class TestRunTranscribeRecordingHappyPath:
    async def test_transcribes_and_marks_completed(self):
        recording = _make_recording()
        org_id = uuid.uuid4()
        transcript = _make_transcript(recording_id=recording.id, status=TranscriptStatus.PENDING)
        result = _make_transcription_result()

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_execute_result((recording, org_id)))
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        speech_service = AsyncMock()
        speech_service.transcribe = AsyncMock(return_value=result)

        storage = AsyncMock()
        storage.load = AsyncMock(return_value=b"audio-bytes")

        transcript_repo = AsyncMock()
        analysis_dispatcher = MagicMock()
        with (
            patch(
                "app.workers.speech_transcription.AssessmentTranscriptRepository",
                return_value=transcript_repo,
            ),
            patch(
                "app.workers.speech_transcription.AssessmentTranscriptService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=transcript)
            mock_service.start_processing = AsyncMock(return_value=transcript)
            mock_service.complete_processing = AsyncMock(return_value=transcript)

            await _run_transcribe_recording(
                str(recording.id),
                _session_factory=session_factory,
                _speech_service=speech_service,
                _storage=storage,
                _analysis_dispatcher=analysis_dispatcher,
            )

            mock_service.create_pending.assert_awaited_once_with(recording.id, org_id)
            mock_service.start_processing.assert_awaited_once_with(recording.id)
            storage.load.assert_awaited_once_with(recording.storage_path)
            speech_service.transcribe.assert_awaited_once_with(
                b"audio-bytes", mime_type=recording.mime_type, filename=recording.filename
            )
            mock_service.complete_processing.assert_awaited_once_with(
                recording.id,
                transcript=result.transcript,
                language=result.language,
                model_name=result.model_name,
                processing_time_ms=1500,
                segment_count=0,
            )
        assert session.commit.await_count == 2
        analysis_dispatcher.assert_called_once_with(str(transcript.id), recording.duration_seconds)

    async def test_listen_repeat_recording_dispatches_listen_repeat_analysis(self):
        recording = _make_recording(recording_type=RecordingType.LISTEN_REPEAT)
        org_id = uuid.uuid4()
        transcript = _make_transcript(recording_id=recording.id, status=TranscriptStatus.PENDING)
        result = _make_transcription_result()

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_execute_result((recording, org_id)))
        session.commit = AsyncMock()
        session_factory = _make_session_factory(session)

        speech_service = AsyncMock()
        speech_service.transcribe = AsyncMock(return_value=result)
        storage = AsyncMock()
        storage.load = AsyncMock(return_value=b"audio-bytes")
        analysis_dispatcher = MagicMock()
        listen_repeat_dispatcher = MagicMock()

        with (
            patch("app.workers.speech_transcription.AssessmentTranscriptRepository"),
            patch(
                "app.workers.speech_transcription.AssessmentTranscriptService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=transcript)
            mock_service.start_processing = AsyncMock(return_value=transcript)
            mock_service.complete_processing = AsyncMock(return_value=transcript)

            await _run_transcribe_recording(
                str(recording.id),
                _session_factory=session_factory,
                _speech_service=speech_service,
                _storage=storage,
                _analysis_dispatcher=analysis_dispatcher,
                _listen_repeat_analysis_dispatcher=listen_repeat_dispatcher,
            )

        analysis_dispatcher.assert_not_called()
        listen_repeat_dispatcher.assert_called_once_with(
            str(transcript.id), recording.duration_seconds
        )

    async def test_recording_not_found_returns_silently(self):
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_execute_result(None))
        session_factory = _make_session_factory(session)

        await _run_transcribe_recording(
            str(uuid.uuid4()), _session_factory=session_factory
        )

        session.commit.assert_not_awaited()

    async def test_already_completed_skips_all_work(self):
        recording = _make_recording()
        org_id = uuid.uuid4()
        transcript = _make_transcript(recording_id=recording.id, status=TranscriptStatus.COMPLETED)

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_make_execute_result((recording, org_id)))
        session_factory = _make_session_factory(session)
        speech_service = AsyncMock()
        storage = AsyncMock()

        with (
            patch("app.workers.speech_transcription.AssessmentTranscriptRepository"),
            patch(
                "app.workers.speech_transcription.AssessmentTranscriptService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.create_pending = AsyncMock(return_value=transcript)

            await _run_transcribe_recording(
                str(recording.id),
                _session_factory=session_factory,
                _speech_service=speech_service,
                _storage=storage,
            )

            mock_service.start_processing.assert_not_called()
        speech_service.transcribe.assert_not_called()
        storage.load.assert_not_called()


# ── _mark_failed ──────────────────────────────────────────────────────────────


class TestMarkFailed:
    async def test_sets_status_and_error_message(self):
        recording_id = uuid.uuid4()
        session = AsyncMock()
        session_factory = _make_session_factory(session)

        with (
            patch("app.workers.speech_transcription.AssessmentTranscriptRepository"),
            patch(
                "app.workers.speech_transcription.AssessmentTranscriptService"
            ) as mock_service_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_service.fail_processing = AsyncMock()

            await _mark_failed(str(recording_id), "something went wrong", _session_factory=session_factory)

            mock_service.fail_processing.assert_awaited_once_with(
                recording_id, "something went wrong"
            )
        session.commit.assert_awaited_once()

    async def test_db_error_is_swallowed(self):
        session_factory = MagicMock(side_effect=RuntimeError("DB is down"))

        await _mark_failed(str(uuid.uuid4()), "original error", _session_factory=session_factory)


# ── _transcribe_recording_task (Celery error classification) ────────────────


class TestCeleryTaskErrorClassification:
    def _make_self(self, retries: int = 0) -> MagicMock:
        mock_self = MagicMock()
        mock_self.request.retries = retries
        mock_self.retry.side_effect = Retry()
        return mock_self

    def test_audio_validation_error_raises_without_retry(self):
        mock_self = self._make_self()
        exc = AudioValidationError("Unsupported audio type")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(AudioValidationError):
                _transcribe_recording_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()

    def test_transcription_error_triggers_retry_with_backoff(self):
        mock_self = self._make_self(retries=0)
        exc = TranscriptionError("Whisper failed to transcribe audio: bad file")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _transcribe_recording_task(mock_self, "some-uuid")

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
                _transcribe_recording_task(mock_self, "some-uuid")

        _, retry_kwargs = mock_self.retry.call_args
        assert retry_kwargs["countdown"] == 120  # 30 * 2^2

    def test_unexpected_exception_triggers_retry(self):
        mock_self = self._make_self()
        exc = ConnectionError("network blip")

        def fake_run(coro):
            raise exc

        with patch("asyncio.run", fake_run):
            with pytest.raises(Retry):
                _transcribe_recording_task(mock_self, "some-uuid")

        mock_self.retry.assert_called_once()

    def test_happy_path_completes_without_retry(self):
        mock_self = self._make_self()

        with patch("asyncio.run", lambda coro: None):
            _transcribe_recording_task(mock_self, "some-uuid")

        mock_self.retry.assert_not_called()

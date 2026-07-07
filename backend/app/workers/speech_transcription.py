"""
Celery task: transcribe_recording
──────────────────────────────────
Async speech-to-text pipeline for one AssessmentRecording's uploaded audio.
Dispatched automatically right after a recording upload completes (see
app.api.v1.endpoints.assessment_sessions.upload_assessment_recording).

  Phase 1 — Fetch the AssessmentRecording + its owning session's org_id,
            create (idempotently) the AssessmentTranscript row, mark
            PROCESSING (own DB transaction).
  Phase 2 — Load audio bytes via StorageBackend (no DB).
  Phase 3 — Call SpeechService.transcribe (no DB, no Whisper import here —
            SpeechService/WhisperService own that).
  Phase 4 — Persist transcript/language/model/timing, mark COMPLETED
            (own DB transaction).

Retry policy     : up to 3 retries with exponential back-off (30 s, 60 s, 120 s).
Permanent errors : AudioValidationError — bad/missing/oversized audio, retrying
                    the same bytes won't help.
Transient errors : ModelLoadError, TranscriptionError, and unexpected
                    exceptions — retried up to the limit.

Idempotency      : A recording whose transcript is already COMPLETED is
                    silently skipped. A retry re-fetches the row and updates
                    it in place.

Phase 5 dispatches app.workers.communication_analysis.analyze_read_aloud for
READ_ALOUD recordings and analyze_listen_repeat for LISTEN_REPEAT
recordings. The transcription task never waits on analysis; it's a fire-and-
forget .delay() exactly like resume_parser's embedding-generation dispatch.
"""

import logging
import uuid
from typing import Any

from celery import Task
from sqlalchemy import select

from app.ai.speech.exceptions import AudioValidationError
from app.ai.speech.speech_service import SpeechService
from app.db.session import AsyncSessionLocal
from app.models.assessment_recording import AssessmentRecording, RecordingType
from app.models.assessment_session import AssessmentSession
from app.models.assessment_transcript import TranscriptStatus
from app.repositories.assessment_transcript import AssessmentTranscriptRepository
from app.services.assessment_transcript import AssessmentTranscriptService
from app.storage.factory import get_storage_backend
from app.workers.celery_app import celery_app, run_task
from app.workers.communication_analysis import analyze_listen_repeat, analyze_read_aloud

logger = logging.getLogger(__name__)


def _enqueue_read_aloud_analysis(transcript_id: str, duration_seconds: float) -> None:
    analyze_read_aloud.delay(transcript_id, duration_seconds)


def _enqueue_listen_repeat_analysis(transcript_id: str, duration_seconds: float) -> None:
    analyze_listen_repeat.delay(transcript_id, duration_seconds)


# ── Private helpers ───────────────────────────────────────────────────────────


async def _get_recording_with_org(
    session: Any, recording_id: uuid.UUID
) -> tuple[AssessmentRecording, uuid.UUID] | None:
    """Fetch an AssessmentRecording alongside its owning session's org_id,
    without requiring the caller to already know the org (mirrors
    resume_parser._get_campaign_org_id)."""
    result = await session.execute(
        select(AssessmentRecording, AssessmentSession.org_id)
        .join(AssessmentSession, AssessmentRecording.session_id == AssessmentSession.id)
        .where(AssessmentRecording.id == recording_id)
    )
    return result.first()


# ── Core async implementation ─────────────────────────────────────────────────


async def _run_transcribe_recording(
    recording_id_str: str,
    *,
    _session_factory: Any = None,
    _speech_service: Any = None,
    _storage: Any = None,
    _analysis_dispatcher: Any = None,
    _listen_repeat_analysis_dispatcher: Any = None,
) -> None:
    """Full transcription workflow. Accepts optional overrides for testability."""
    factory = _session_factory or AsyncSessionLocal
    speech_service = _speech_service or SpeechService()
    storage = _storage or get_storage_backend()
    dispatch_analysis = _analysis_dispatcher or _enqueue_read_aloud_analysis
    dispatch_listen_repeat_analysis = (
        _listen_repeat_analysis_dispatcher or _enqueue_listen_repeat_analysis
    )
    recording_id = uuid.UUID(recording_id_str)
    log_ctx = {"recording_id": recording_id_str}

    # ── Phase 1: Fetch + create/fetch transcript + mark PROCESSING ──────────
    async with factory() as session:
        row = await _get_recording_with_org(session, recording_id)
        if row is None:
            logger.warning("AssessmentRecording not found — nothing to do", extra=log_ctx)
            return
        recording, org_id = row

        transcript_repo = AssessmentTranscriptRepository(session)
        service = AssessmentTranscriptService(transcript_repo)
        transcript = await service.create_pending(recording_id, org_id)

        if transcript.status == TranscriptStatus.COMPLETED:
            logger.info("Transcript already completed — idempotent skip", extra=log_ctx)
            return

        logger.info(
            "Task Started",
            extra={**log_ctx, "transcript_id": str(transcript.id)},
        )
        transcript = await service.start_processing(recording_id)
        await session.commit()

        storage_path: str = recording.storage_path
        mime_type: str = recording.mime_type
        filename: str = recording.filename
        recording_type: RecordingType = recording.recording_type
        duration_seconds: float = recording.duration_seconds
        transcript_id: uuid.UUID = transcript.id

    # ── Phase 2: Load audio bytes ─────────────────────────────────────────────
    audio_bytes = await storage.load(storage_path)

    # ── Phase 3: Transcribe ────────────────────────────────────────────────────
    result = await speech_service.transcribe(audio_bytes, mime_type=mime_type, filename=filename)

    # ── Phase 4: Persist results ──────────────────────────────────────────────
    processing_time_ms = int(result.processing_time_seconds * 1000)
    async with factory() as session:
        transcript_repo = AssessmentTranscriptRepository(session)
        service = AssessmentTranscriptService(transcript_repo)
        await service.complete_processing(
            recording_id,
            transcript=result.transcript,
            language=result.language,
            model_name=result.model_name,
            processing_time_ms=processing_time_ms,
            segment_count=len(result.segments),
        )
        await session.commit()
        logger.info(
            "Task Completed",
            extra={
                **log_ctx,
                "transcript_id": str(transcript_id),
                "processing_time_ms": processing_time_ms,
            },
        )

    # ── Phase 5: Dispatch communication analysis, by recording type ─────────
    if recording_type == RecordingType.READ_ALOUD:
        dispatch_analysis(str(transcript_id), duration_seconds)
        logger.info(
            "Dispatched Read Aloud analysis",
            extra={**log_ctx, "transcript_id": str(transcript_id)},
        )
    elif recording_type == RecordingType.LISTEN_REPEAT:
        dispatch_listen_repeat_analysis(str(transcript_id), duration_seconds)
        logger.info(
            "Dispatched Listen & Repeat analysis",
            extra={**log_ctx, "transcript_id": str(transcript_id)},
        )


async def _mark_failed(
    recording_id_str: str,
    error: str,
    *,
    _session_factory: Any = None,
) -> None:
    """Best-effort: set the AssessmentTranscript status to FAILED with an
    error message."""
    factory = _session_factory or AsyncSessionLocal
    try:
        recording_id = uuid.UUID(recording_id_str)
        async with factory() as session:
            transcript_repo = AssessmentTranscriptRepository(session)
            service = AssessmentTranscriptService(transcript_repo)
            await service.fail_processing(recording_id, error[:1000])
            await session.commit()
    except Exception as exc:
        logger.error(
            "Task Failed — could not persist FAILED status",
            extra={"recording_id": recording_id_str, "mark_error": str(exc)},
        )


# ── Celery task (sync entry point) ────────────────────────────────────────────


async def _run_transcribe_recording_with_recovery(recording_id: str) -> None:
    """Runs the transcription workflow and, on failure, persists the FAILED
    status in the same coroutine/event loop as the work itself (see
    celery_app.run_task's docstring / resume_parser's equivalent wrapper for
    why a second, separate asyncio.run() call for _mark_failed is unsafe)."""
    try:
        await _run_transcribe_recording(recording_id)
    except AudioValidationError as exc:
        await _mark_failed(recording_id, f"Audio validation failed: {exc}")
        raise
    except Exception as exc:
        await _mark_failed(recording_id, str(exc)[:1000])
        raise


def _transcribe_recording_task(self: Task, recording_id: str) -> None:
    """
    Core task logic extracted from the decorator for direct testability.
    Classifies errors into: permanent (no retry) vs transient (retry with backoff).
    """
    log_ctx = {"recording_id": recording_id, "attempt": self.request.retries + 1}
    logger.info("Task started", extra=log_ctx)

    try:
        run_task(_run_transcribe_recording_with_recovery(recording_id))
        logger.info("Task completed", extra=log_ctx)

    except AudioValidationError as exc:
        # Permanent — bad/oversized/unsupported audio won't become valid on retry
        logger.error("Audio validation failed (permanent)", extra={**log_ctx, "error": str(exc)})
        raise  # Celery marks task as FAILURE

    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)
        logger.warning(
            "Task Retried",
            extra={**log_ctx, "error": str(exc), "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.speech_transcription.transcribe_recording",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def transcribe_recording(self: Task, recording_id: str) -> None:
    """Entry point registered with Celery. Delegates to _transcribe_recording_task."""
    _transcribe_recording_task(self, recording_id)

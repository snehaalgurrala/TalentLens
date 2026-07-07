"""
Celery tasks: analyze_read_aloud, analyze_listen_repeat
─────────────────────────────────────────────────────────
Deterministic communication-metrics pipelines for one completed
AssessmentTranscript. analyze_read_aloud is dispatched automatically right
after transcription completes for a READ_ALOUD recording, and
analyze_listen_repeat for a LISTEN_REPEAT recording (see
app.workers.speech_transcription._run_transcribe_recording).

Both tasks share the same 3-phase shape:
  Phase 1 — Fetch the AssessmentTranscript, create (idempotently) the
            AssessmentAnalysis row (own DB transaction).
  Phase 2 — Compare the transcript against the fixed reference sentence and
            compute metrics (no DB, no LLM — pure deterministic text/
            embedding comparison, see app.ai.communication).
  Phase 3 — Persist metrics/detail, mark COMPLETED (own DB transaction).

Unlike transcribe_recording, there is no external model call to isolate
here — analysis is pure CPU-bound Python (plus one local embedding-model
call for Listen & Repeat) with no I/O beyond the two DB transactions, so a
failure partway through is almost always a bug rather than a transient
blip. Both tasks are still retried up to 3 times with the same backoff as
every other worker in this codebase, in case of a genuine DB hiccup
mid-transaction.

Idempotency      : An AssessmentTranscript whose analysis is already
                    COMPLETED is silently skipped. A retry re-fetches the
                    row and updates it in place.
"""

import logging
import uuid
from typing import Any

from celery import Task

from app.ai.communication.analysis_service import (
    ListenRepeatAnalysisService,
    ReadAloudAnalysisService,
)
from app.ai.communication.config import (
    get_listen_repeat_reference_sentence,
    get_read_aloud_reference_sentence,
)
from app.ai.communication.exceptions import CommunicationAnalysisError
from app.db.session import AsyncSessionLocal
from app.models.assessment_analysis import AnalysisStatus, AnalysisType
from app.models.assessment_transcript import AssessmentTranscript, TranscriptStatus
from app.repositories.assessment_analysis import AssessmentAnalysisRepository
from app.services.assessment_analysis import AssessmentAnalysisService
from app.workers.celery_app import celery_app, run_task

logger = logging.getLogger(__name__)


# ── Core async implementation ─────────────────────────────────────────────────


async def _run_analyze_read_aloud(
    transcript_id_str: str,
    duration_seconds: float,
    *,
    _session_factory: Any = None,
    _analysis_service: Any = None,
) -> None:
    """Full Read Aloud analysis workflow. Accepts optional overrides for testability."""
    factory = _session_factory or AsyncSessionLocal
    analysis_service = _analysis_service or ReadAloudAnalysisService()
    transcript_id = uuid.UUID(transcript_id_str)
    log_ctx = {"transcript_id": transcript_id_str}

    # ── Phase 1: Fetch transcript + create/fetch analysis row ───────────────
    async with factory() as session:
        transcript = await session.get(AssessmentTranscript, transcript_id)
        if transcript is None:
            logger.warning("AssessmentTranscript not found — nothing to do", extra=log_ctx)
            return
        if transcript.status != TranscriptStatus.COMPLETED:
            logger.warning(
                "AssessmentTranscript not COMPLETED — nothing to analyze",
                extra={**log_ctx, "transcript_status": transcript.status.value},
            )
            return

        analysis_repo = AssessmentAnalysisRepository(session)
        service = AssessmentAnalysisService(analysis_repo)
        analysis = await service.create_pending(transcript_id, transcript.organization_id)

        if analysis.status == AnalysisStatus.COMPLETED:
            logger.info("Analysis already completed — idempotent skip", extra=log_ctx)
            return

        logger.info("Task Started", extra={**log_ctx, "analysis_id": str(analysis.id)})
        await session.commit()

        # Capture scalars before the session closes (expire_on_commit=False preserves them)
        transcript_text: str = transcript.transcript or ""

    # ── Phase 2: Compare + score (no DB, no LLM) ─────────────────────────────
    reference_sentence = get_read_aloud_reference_sentence()
    result = analysis_service.analyze(reference_sentence, transcript_text, duration_seconds)

    # ── Phase 3: Persist results ──────────────────────────────────────────────
    async with factory() as session:
        analysis_repo = AssessmentAnalysisRepository(session)
        service = AssessmentAnalysisService(analysis_repo)
        metrics = result.metrics
        await service.complete_processing(
            transcript_id,
            overall_score=metrics.overall_score,
            word_accuracy=metrics.word_accuracy,
            correct_words=metrics.correct_words,
            missing_words=metrics.missing_words,
            extra_words=metrics.extra_words,
            substituted_words=metrics.substituted_words,
            total_words=metrics.total_words,
            reading_speed_wpm=metrics.reading_speed_wpm,
            completion_percentage=metrics.completion_percentage,
            analysis_json=result.comparison.model_dump(mode="json"),
        )
        await session.commit()
        logger.info(
            "Task Completed",
            extra={**log_ctx, "overall_score": metrics.overall_score},
        )


async def _run_analyze_listen_repeat(
    transcript_id_str: str,
    duration_seconds: float,
    *,
    _session_factory: Any = None,
    _analysis_service: Any = None,
) -> None:
    """Full Listen & Repeat analysis workflow. Accepts optional overrides for testability."""
    factory = _session_factory or AsyncSessionLocal
    analysis_service = _analysis_service or ListenRepeatAnalysisService()
    transcript_id = uuid.UUID(transcript_id_str)
    log_ctx = {"transcript_id": transcript_id_str}

    # ── Phase 1: Fetch transcript + create/fetch analysis row ───────────────
    async with factory() as session:
        transcript = await session.get(AssessmentTranscript, transcript_id)
        if transcript is None:
            logger.warning("AssessmentTranscript not found — nothing to do", extra=log_ctx)
            return
        if transcript.status != TranscriptStatus.COMPLETED:
            logger.warning(
                "AssessmentTranscript not COMPLETED — nothing to analyze",
                extra={**log_ctx, "transcript_status": transcript.status.value},
            )
            return

        analysis_repo = AssessmentAnalysisRepository(session)
        service = AssessmentAnalysisService(analysis_repo)
        analysis = await service.create_pending(
            transcript_id, transcript.organization_id, analysis_type=AnalysisType.LISTEN_REPEAT
        )

        if analysis.status == AnalysisStatus.COMPLETED:
            logger.info("Analysis already completed — idempotent skip", extra=log_ctx)
            return

        logger.info("Task Started", extra={**log_ctx, "analysis_id": str(analysis.id)})
        await session.commit()

        # Capture scalars before the session closes (expire_on_commit=False preserves them)
        transcript_text: str = transcript.transcript or ""

    # ── Phase 2: Compare + score (no DB, no LLM) ─────────────────────────────
    reference_sentence = get_listen_repeat_reference_sentence()
    result = analysis_service.analyze(reference_sentence, transcript_text, duration_seconds)

    # ── Phase 3: Persist results ──────────────────────────────────────────────
    async with factory() as session:
        analysis_repo = AssessmentAnalysisRepository(session)
        service = AssessmentAnalysisService(analysis_repo)
        metrics = result.metrics
        await service.complete_listen_repeat_processing(
            transcript_id,
            overall_score=metrics.overall_score,
            semantic_similarity=metrics.semantic_similarity,
            keyword_coverage=metrics.keyword_coverage,
            completion_percentage=metrics.completion_percentage,
            analysis_json=metrics.model_dump(mode="json"),
        )
        await session.commit()
        logger.info(
            "Task Completed",
            extra={**log_ctx, "overall_score": metrics.overall_score},
        )


async def _mark_failed(
    transcript_id_str: str,
    error: str,
    *,
    _session_factory: Any = None,
) -> None:
    """Best-effort: set the AssessmentAnalysis status to FAILED with an
    error message."""
    factory = _session_factory or AsyncSessionLocal
    try:
        transcript_id = uuid.UUID(transcript_id_str)
        async with factory() as session:
            analysis_repo = AssessmentAnalysisRepository(session)
            service = AssessmentAnalysisService(analysis_repo)
            await service.fail_processing(transcript_id, error[:1000])
            await session.commit()
    except Exception as exc:
        logger.error(
            "Task Failed — could not persist FAILED status",
            extra={"transcript_id": transcript_id_str, "mark_error": str(exc)},
        )


# ── Celery task (sync entry point) ────────────────────────────────────────────


async def _run_analyze_read_aloud_with_recovery(
    transcript_id: str, duration_seconds: float
) -> None:
    """Runs the analysis workflow and, on failure, persists the FAILED
    status in the same coroutine/event loop as the work itself (see
    celery_app.run_task's docstring for why a second, separate asyncio.run()
    call for _mark_failed is unsafe)."""
    try:
        await _run_analyze_read_aloud(transcript_id, duration_seconds)
    except CommunicationAnalysisError as exc:
        await _mark_failed(transcript_id, f"Analysis input invalid: {exc}")
        raise
    except Exception as exc:
        await _mark_failed(transcript_id, str(exc)[:1000])
        raise


def _analyze_read_aloud_task(self: Task, transcript_id: str, duration_seconds: float) -> None:
    """
    Core task logic extracted from the decorator for direct testability.
    Classifies errors into: permanent (no retry) vs transient (retry with backoff).
    """
    log_ctx = {"transcript_id": transcript_id, "attempt": self.request.retries + 1}
    logger.info("Task started", extra=log_ctx)

    try:
        run_task(_run_analyze_read_aloud_with_recovery(transcript_id, duration_seconds))
        logger.info("Task completed", extra=log_ctx)

    except CommunicationAnalysisError as exc:
        # Permanent — a bad/negative duration won't become valid on retry
        logger.error("Analysis input invalid (permanent)", extra={**log_ctx, "error": str(exc)})
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
    name="app.workers.communication_analysis.analyze_read_aloud",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def analyze_read_aloud(self: Task, transcript_id: str, duration_seconds: float) -> None:
    """Entry point registered with Celery. Delegates to _analyze_read_aloud_task."""
    _analyze_read_aloud_task(self, transcript_id, duration_seconds)


async def _run_analyze_listen_repeat_with_recovery(
    transcript_id: str, duration_seconds: float
) -> None:
    """Runs the analysis workflow and, on failure, persists the FAILED
    status in the same coroutine/event loop as the work itself (see
    celery_app.run_task's docstring for why a second, separate asyncio.run()
    call for _mark_failed is unsafe)."""
    try:
        await _run_analyze_listen_repeat(transcript_id, duration_seconds)
    except CommunicationAnalysisError as exc:
        await _mark_failed(transcript_id, f"Analysis input invalid: {exc}")
        raise
    except Exception as exc:
        await _mark_failed(transcript_id, str(exc)[:1000])
        raise


def _analyze_listen_repeat_task(self: Task, transcript_id: str, duration_seconds: float) -> None:
    """
    Core task logic extracted from the decorator for direct testability.
    Classifies errors into: permanent (no retry) vs transient (retry with backoff).
    """
    log_ctx = {"transcript_id": transcript_id, "attempt": self.request.retries + 1}
    logger.info("Task started", extra=log_ctx)

    try:
        run_task(_run_analyze_listen_repeat_with_recovery(transcript_id, duration_seconds))
        logger.info("Task completed", extra=log_ctx)

    except CommunicationAnalysisError as exc:
        # Permanent — a bad/negative duration won't become valid on retry
        logger.error("Analysis input invalid (permanent)", extra={**log_ctx, "error": str(exc)})
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
    name="app.workers.communication_analysis.analyze_listen_repeat",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def analyze_listen_repeat(self: Task, transcript_id: str, duration_seconds: float) -> None:
    """Entry point registered with Celery. Delegates to _analyze_listen_repeat_task."""
    _analyze_listen_repeat_task(self, transcript_id, duration_seconds)

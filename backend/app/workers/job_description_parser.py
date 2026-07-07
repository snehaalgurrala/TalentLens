"""
Celery task: parse_job_description
───────────────────────────────────
Full parsing workflow for a single JobDescription. The raw text is already
stored on the row at creation time (upload or paste), so unlike resume
parsing there is no extraction phase here.

  Phase 1 — Fetch + mark PROCESSING (own DB transaction).
  Phase 2 — POST raw_text to the AI service, receive structured JSON (no DB).
  Phase 3 — Persist structured_json + parser_version + parsed_at, mark COMPLETED
            (own DB transaction).
  Phase 4 — Dispatch generate_job_description_embedding (separate task, own retries).

Retry policy      : up to 3 retries with exponential back-off (30 s, 60 s, 120 s).
Permanent errors   : 4xx AI responses — no retry, status → FAILED.
Transient errors   : 5xx AI responses and unexpected exceptions — retry up to limit.

Idempotency        : A job description already in COMPLETED state is silently skipped.
                      A retry re-fetches the row and updates it in place.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from celery import Task

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.job_description import ParsingStatus
from app.repositories.job_description import JobDescriptionRepository
from app.workers.celery_app import celery_app, run_task
from app.workers.embedding_worker import generate_job_description_embedding

logger = logging.getLogger(__name__)

_PARSER_VERSION = "v1"


# ── Private helpers ───────────────────────────────────────────────────────────


async def _call_ai_service(
    text: str,
    *,
    _client: httpx.AsyncClient | None = None,
) -> dict:
    """POST job description text to the AI parsing endpoint; returns the structured JSON."""

    async def _request(client: httpx.AsyncClient) -> dict:
        resp = await client.post(
            f"{settings.AI_SERVICE_URL}/parse-job-description",
            json={"jd_text": text, "parser_version": _PARSER_VERSION},
        )
        resp.raise_for_status()
        return resp.json()

    if _client is not None:
        return await _request(_client)
    async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT) as client:
        return await _request(client)


# ── Core async implementation ─────────────────────────────────────────────────


def _enqueue_job_description_embedding(job_description_id: str) -> None:
    generate_job_description_embedding.delay(job_description_id)


async def _run_parse_job_description(
    job_description_id_str: str,
    *,
    _session_factory: Any = None,
    _http_client: httpx.AsyncClient | None = None,
    _embedding_dispatcher: Any = None,
) -> None:
    """Full parse workflow. Accepts optional overrides for testability."""
    factory = _session_factory or AsyncSessionLocal
    dispatch_embedding = _embedding_dispatcher or _enqueue_job_description_embedding
    jd_id = uuid.UUID(job_description_id_str)
    log_ctx = {"job_description_id": job_description_id_str}

    # ── Phase 1: Fetch + mark PROCESSING ─────────────────────────────────────
    async with factory() as session:
        repo = JobDescriptionRepository(session)
        jd = await repo.get_by_id(jd_id)

        if jd is None:
            logger.warning("JobDescription not found — nothing to do", extra=log_ctx)
            return

        if jd.parsing_status == ParsingStatus.COMPLETED:
            logger.info("JobDescription already parsed — idempotent skip", extra=log_ctx)
            return

        logger.info(
            "Starting parse",
            extra={**log_ctx, "status": jd.parsing_status.value},
        )
        await repo.update(jd, parsing_status=ParsingStatus.PROCESSING, parsing_error=None)
        await session.commit()

        # Capture scalars before the session closes (expire_on_commit=False preserves them)
        raw_text: str = jd.raw_text

    # ── Phase 2: Call AI service ──────────────────────────────────────────────
    logger.info("Calling AI service", extra={**log_ctx, "url": settings.AI_SERVICE_URL})
    ai_data = await _call_ai_service(raw_text, _client=_http_client)
    job = ai_data.get("job")
    structured_jd = ai_data.get("structured_jd")
    if job is None or structured_jd is None:
        raise ValueError("AI service response is missing 'job' and/or 'structured_jd'.")
    structured = {
        "job": job,
        "structured_jd": structured_jd,
        "confidence": ai_data.get("confidence"),
    }
    logger.info(
        "AI service response received",
        extra={
            **log_ctx,
            "job_keys": list(job.keys()),
            "structured_jd_keys": list(structured_jd.keys()),
        },
    )

    # ── Phase 3: Persist results ──────────────────────────────────────────────
    async with factory() as session:
        repo = JobDescriptionRepository(session)
        jd = await repo.get_by_id(jd_id)
        if jd is None:
            logger.warning("JobDescription disappeared before persist", extra=log_ctx)
            return

        await repo.update(
            jd,
            structured_json=structured,
            parser_version=_PARSER_VERSION,
            parsed_at=datetime.now(UTC),
            parsing_status=ParsingStatus.COMPLETED,
            parsing_error=None,
        )
        await session.commit()
        logger.info("JobDescription marked COMPLETED", extra=log_ctx)

    # ── Phase 4: Dispatch embedding generation ───────────────────────────────
    dispatch_embedding(job_description_id_str)
    logger.info("Dispatched embedding generation", extra=log_ctx)


async def _mark_failed(
    job_description_id_str: str,
    error: str,
    *,
    _session_factory: Any = None,
) -> None:
    """Best-effort: set JobDescription status to FAILED with an error message."""
    factory = _session_factory or AsyncSessionLocal
    try:
        jd_id = uuid.UUID(job_description_id_str)
        async with factory() as session:
            repo = JobDescriptionRepository(session)
            jd = await repo.get_by_id(jd_id)
            if jd is not None:
                await repo.update(
                    jd,
                    parsing_status=ParsingStatus.FAILED,
                    parsing_error=error[:1000],
                )
            await session.commit()
    except Exception as exc:
        logger.error(
            "Could not persist FAILED status",
            extra={"job_description_id": job_description_id_str, "mark_error": str(exc)},
        )


# ── Celery task (sync entry point) ────────────────────────────────────────────


async def _run_parse_job_description_with_recovery(job_description_id: str) -> None:
    """Runs the parse workflow and, on failure, persists the FAILED status in
    the same coroutine/event loop as the work itself, via a single run_task()
    call in _parse_job_description_task below. See
    resume_parser._run_parse_resume_with_recovery and celery_app.run_task for
    why a second, separate asyncio.run() call for _mark_failed is unsafe
    here: it hands AsyncSessionLocal's connection pool a connection tied to
    a different event loop, raising 'RuntimeError: Event loop is closed'
    and silently swallowing the failure.
    """
    try:
        await _run_parse_job_description(job_description_id)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code < 500:
            await _mark_failed(job_description_id, f"AI service {status_code}: {exc}")
        else:
            await _mark_failed(job_description_id, f"AI service 5xx ({status_code})")
        raise
    except Exception as exc:
        await _mark_failed(job_description_id, str(exc)[:1000])
        raise


def _parse_job_description_task(self: Task, job_description_id: str) -> None:
    """
    Core task logic extracted from the decorator for direct testability.
    Classifies errors into: permanent (no retry) vs transient (retry with backoff).
    """
    log_ctx = {"job_description_id": job_description_id, "attempt": self.request.retries + 1}
    logger.info("Task started", extra=log_ctx)

    try:
        run_task(_run_parse_job_description_with_recovery(job_description_id))
        logger.info("Task completed", extra=log_ctx)

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code < 500:
            # 4xx — bad request or auth; retrying with the same payload won't help
            logger.error(
                "AI service rejected request (permanent)",
                extra={**log_ctx, "http_status": status_code},
            )
            raise  # no retry
        # 5xx — transient server-side error
        countdown = 30 * (2 ** self.request.retries)
        logger.warning(
            "AI service 5xx — retrying",
            extra={**log_ctx, "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)
        logger.exception(
            "Unexpected error — retrying",
            extra={**log_ctx, "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.job_description_parser.parse_job_description",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def parse_job_description(self: Task, job_description_id: str) -> None:
    """Entry point registered with Celery. Delegates to _parse_job_description_task."""
    _parse_job_description_task(self, job_description_id)

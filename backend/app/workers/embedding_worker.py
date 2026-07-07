"""
Celery tasks: generate_resume_embedding / generate_job_description_embedding
─────────────────────────────────────────────────────────────────────────
Dispatched automatically right after resume/job-description parsing
completes (see the end of resume_parser.py / job_description_parser.py).
Generates a local sentence-transformers embedding via LocalEmbeddingService
and persists it — no external API calls, same as the rest of the pipeline.

Retry policy     : up to 3 retries with exponential back-off (30 s, 60 s, 120 s).
Permanent errors : ValueError — the row disappeared or has no structured_json
                   to embed yet; retrying won't help.
Transient errors : model load failures and anything else — retried up to
                   the limit (LocalEmbeddingService already marks the row
                   embedding_status=FAILED before re-raising, so ranking
                   correctly excludes it while the retry is pending).
"""

import logging
import uuid
from typing import Any

from celery import Task

from app.db.session import AsyncSessionLocal
from app.models.candidate_activity import ActivityEventType
from app.models.embedding import EmbeddingStatus
from app.models.resume_file import PipelineStage, is_earlier_pipeline_stage
from app.repositories.candidate_activity import CandidateActivityRepository
from app.repositories.job_description import JobDescriptionRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.resume_file import ResumeFileRepository
from app.services.local_embedding_service import LocalEmbeddingService
from app.workers.celery_app import celery_app, run_task

logger = logging.getLogger(__name__)


# ── Core async implementation ─────────────────────────────────────────────────


async def _run_generate_resume_embedding(
    parsed_resume_id_str: str,
    *,
    _session_factory: Any = None,
) -> None:
    factory = _session_factory or AsyncSessionLocal
    resume_id = uuid.UUID(parsed_resume_id_str)
    async with factory() as session:
        parsed_resume_repo = ParsedResumeRepository(session)
        service = LocalEmbeddingService(parsed_resume_repo, JobDescriptionRepository(session))
        try:
            parsed_resume = await service.embed_resume(resume_id)
            if parsed_resume.embedding_status == EmbeddingStatus.READY:
                rf_repo = ResumeFileRepository(session)
                rf = await rf_repo.get_by_id(parsed_resume.resume_file_id)
                if rf is not None and is_earlier_pipeline_stage(
                    rf.pipeline_stage, PipelineStage.RANKED
                ):
                    await rf_repo.update(rf, pipeline_stage=PipelineStage.RANKED)
                    await CandidateActivityRepository(session).create(
                        rf.id, None, ActivityEventType.RANKED
                    )
        finally:
            # Commit whatever state was reached (READY, or FAILED as set
            # internally by the service) even if an exception is about to
            # propagate — otherwise closing the session on the exception
            # path would silently roll the FAILED marker back too.
            await session.commit()


async def _run_generate_job_description_embedding(
    job_description_id_str: str,
    *,
    _session_factory: Any = None,
) -> None:
    factory = _session_factory or AsyncSessionLocal
    jd_id = uuid.UUID(job_description_id_str)
    async with factory() as session:
        service = LocalEmbeddingService(
            ParsedResumeRepository(session), JobDescriptionRepository(session)
        )
        try:
            await service.embed_job_description(jd_id)
        finally:
            await session.commit()


# ── Celery tasks (sync entry points) ──────────────────────────────────────────


def _generate_resume_embedding_task(self: Task, parsed_resume_id: str) -> None:
    log_ctx = {"parsed_resume_id": parsed_resume_id, "attempt": self.request.retries + 1}
    logger.info("Resume embedding task started", extra=log_ctx)
    try:
        run_task(_run_generate_resume_embedding(parsed_resume_id))
        logger.info("Resume embedding task completed", extra=log_ctx)
    except ValueError as exc:
        logger.error("Resume embedding failed (permanent)", extra={**log_ctx, "error": str(exc)})
        raise
    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)
        logger.exception(
            "Resume embedding failed — retrying", extra={**log_ctx, "countdown_s": countdown}
        )
        raise self.retry(exc=exc, countdown=countdown)


def _generate_job_description_embedding_task(self: Task, job_description_id: str) -> None:
    log_ctx = {"job_description_id": job_description_id, "attempt": self.request.retries + 1}
    logger.info("Job description embedding task started", extra=log_ctx)
    try:
        run_task(_run_generate_job_description_embedding(job_description_id))
        logger.info("Job description embedding task completed", extra=log_ctx)
    except ValueError as exc:
        logger.error(
            "Job description embedding failed (permanent)", extra={**log_ctx, "error": str(exc)}
        )
        raise
    except Exception as exc:
        countdown = 30 * (2 ** self.request.retries)
        logger.exception(
            "Job description embedding failed — retrying",
            extra={**log_ctx, "countdown_s": countdown},
        )
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    bind=True,
    name="app.workers.embedding_worker.generate_resume_embedding",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_resume_embedding(self: Task, parsed_resume_id: str) -> None:
    """Entry point registered with Celery. Delegates to _generate_resume_embedding_task."""
    _generate_resume_embedding_task(self, parsed_resume_id)


@celery_app.task(
    bind=True,
    name="app.workers.embedding_worker.generate_job_description_embedding",
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
)
def generate_job_description_embedding(self: Task, job_description_id: str) -> None:
    """Entry point registered with Celery. Delegates to _generate_job_description_embedding_task."""
    _generate_job_description_embedding_task(self, job_description_id)

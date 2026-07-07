import asyncio
from collections.abc import Coroutine
from typing import Any

from celery import Celery

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging(settings.LOG_LEVEL)

celery_app = Celery(
    "talentlens",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.resume_parser",
        "app.workers.job_description_parser",
        "app.workers.embedding_worker",
        "app.workers.speech_transcription",
        "app.workers.communication_analysis",
        "app.workers.communication_assessment",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)


def run_task(coro: Coroutine[Any, Any, None]) -> None:
    """Run a Celery task's async body in a fresh event loop, then dispose of
    the shared AsyncSessionLocal engine's connection pool before that loop
    closes.

    AsyncSessionLocal's engine is a module-level singleton, created once per
    forked worker process and reused by every task that process ever runs.
    Each task invocation gets its own event loop via this helper (like a bare
    asyncio.run() would), but a pooled asyncpg connection checked back in at
    the end of one task's loop is bound to that loop — so the next task in
    the same process to check it out hits "Future attached to a different
    loop" / "Event loop is closed". Disposing the pool here, still inside the
    loop that used it, discards those connections before they can leak into
    the next task's loop instead of leaving that failure for whichever task
    happens to run next.
    """

    async def _wrapped() -> None:
        from app.db.session import engine

        try:
            await coro
        finally:
            await engine.dispose()

    asyncio.run(_wrapped())

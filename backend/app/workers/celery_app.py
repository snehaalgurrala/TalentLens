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

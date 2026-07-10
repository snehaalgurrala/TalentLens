import asyncio
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.speech.whisper_service import is_loaded as whisper_is_loaded
from app.core.config import settings
from app.core.redis import get_redis_client
from app.schemas.system_health import CeleryHealth, DiskHealth, SystemHealthChecks, SystemHealthResponse

logger = logging.getLogger(__name__)

_CELERY_QUEUE_NAME = "celery"  # default queue key; unmodified in app.workers.celery_app


class SystemHealthService:
    async def get_report(self) -> SystemHealthResponse:
        from app.db.session import engine

        database_status: str = "ok"
        try:
            async with AsyncSession(engine) as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning("System health: database check failed: %s", exc)
            database_status = "error"

        redis_status: str = "ok"
        queue_length = 0
        try:
            client = get_redis_client()
            await client.ping()
            queue_length = await client.llen(_CELERY_QUEUE_NAME)
        except RuntimeError:
            redis_status = "not_initialized"
        except Exception as exc:
            logger.warning("System health: redis check failed: %s", exc)
            redis_status = "error"

        celery_health = await self._check_celery()

        whisper_status = "loaded" if whisper_is_loaded() else "not_loaded"

        storage_status, disk_health = self._check_storage()

        overall = "ok"
        if database_status != "ok" or redis_status == "error" or celery_health.status == "down":
            overall = "degraded"

        return SystemHealthResponse(
            status=overall,  # type: ignore[arg-type]
            environment=settings.APP_ENV,
            version=settings.VERSION,
            build=settings.BUILD_NUMBER,
            timestamp=datetime.now(UTC),
            checks=SystemHealthChecks(
                database=database_status,  # type: ignore[arg-type]
                redis=redis_status,  # type: ignore[arg-type]
                celery_workers=celery_health,
                whisper_model=whisper_status,  # type: ignore[arg-type]
                storage=storage_status,  # type: ignore[arg-type]
                disk=disk_health,
                queue_length=queue_length,
            ),
        )

    async def _check_celery(self) -> CeleryHealth:
        def _ping() -> dict[str, Any] | None:
            from app.workers.celery_app import celery_app

            return celery_app.control.inspect(timeout=2).ping()

        try:
            result = await asyncio.wait_for(asyncio.to_thread(_ping), timeout=3)
        except Exception as exc:
            logger.warning("System health: celery check failed: %s", exc)
            result = None

        worker_count = len(result or {})
        return CeleryHealth(status="ok" if worker_count > 0 else "down", worker_count=worker_count)

    def _check_storage(self) -> tuple[str, DiskHealth]:
        path = Path(settings.LOCAL_STORAGE_PATH)
        try:
            path.mkdir(parents=True, exist_ok=True)
            storage_ok = path.exists() and __import__("os").access(path, __import__("os").W_OK)
        except Exception as exc:
            logger.warning("System health: storage check failed: %s", exc)
            storage_ok = False

        try:
            usage = shutil.disk_usage(path if path.exists() else ".")
            disk = DiskHealth(
                used_gb=round((usage.total - usage.free) / (1024**3), 2),
                total_gb=round(usage.total / (1024**3), 2),
                percent_used=round((usage.total - usage.free) / usage.total * 100, 1)
                if usage.total
                else 0.0,
            )
        except Exception as exc:
            logger.warning("System health: disk usage check failed: %s", exc)
            disk = DiskHealth(used_gb=0.0, total_gb=0.0, percent_used=0.0)

        return ("ok" if storage_ok else "error"), disk

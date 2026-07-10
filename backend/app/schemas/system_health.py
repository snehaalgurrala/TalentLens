from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CeleryHealth(BaseModel):
    status: Literal["ok", "down"]
    worker_count: int


class DiskHealth(BaseModel):
    used_gb: float
    total_gb: float
    percent_used: float


class SystemHealthChecks(BaseModel):
    database: Literal["ok", "error"]
    redis: Literal["ok", "error", "not_initialized"]
    celery_workers: CeleryHealth
    whisper_model: Literal["loaded", "not_loaded"]
    storage: Literal["ok", "error"]
    disk: DiskHealth
    queue_length: int


class SystemHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    version: str
    build: str
    timestamp: datetime
    checks: SystemHealthChecks

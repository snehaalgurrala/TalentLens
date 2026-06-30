import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import connect_redis, disconnect_redis, get_redis_client
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting %s v%s [%s]", settings.PROJECT_NAME, settings.VERSION, settings.APP_ENV)

    await connect_redis(settings.REDIS_URL)

    yield

    await disconnect_redis()
    await engine.dispose()
    logger.info("%s shut down cleanly", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered recruitment intelligence platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/", tags=["system"], summary="Project info")
async def root() -> dict[str, Any]:
    return {"project": settings.PROJECT_NAME, "version": settings.VERSION}


@app.get("/health", tags=["system"], summary="Liveness / dependency health check")
async def health_check() -> JSONResponse:
    report: dict[str, Any] = {"status": "ok", "services": {}}

    # ── Database ──────────────────────────────────────────────
    try:
        async with AsyncSession(engine) as session:
            await session.execute(text("SELECT 1"))
        report["services"]["database"] = "ok"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        report["services"]["database"] = "error"
        report["status"] = "degraded"

    # ── Redis ─────────────────────────────────────────────────
    try:
        client = get_redis_client()
        await client.ping()
        report["services"]["redis"] = "ok"
    except RuntimeError:
        report["services"]["redis"] = "not_initialized"
        report["status"] = "degraded"
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        report["services"]["redis"] = "error"
        report["status"] = "degraded"

    http_status = 200 if report["status"] == "ok" else 503
    return JSONResponse(content=report, status_code=http_status)

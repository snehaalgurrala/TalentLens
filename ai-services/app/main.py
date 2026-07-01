from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging
from app.routers import embedding, job_description, parse

setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    yield


app = FastAPI(
    title="TalentLens AI Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(parse.router)
app.include_router(job_description.router)
app.include_router(embedding.router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "service": "ai-service"}

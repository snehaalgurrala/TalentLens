"""
Real-Postgres integration tests (Task 1 / 9 of the hardening sprint).

Point Postgres/Redis env vars at a disposable database before running this
directory, e.g. from `backend/`:

    POSTGRES_HOST=localhost POSTGRES_DB=talentlens_test REDIS_HOST=localhost \
        pytest tests/integration

These tests run real Alembic migrations, hit the API through the app's
normal lifespan, and assert database state via a fresh AsyncSession —
proving writes actually commit (see app/db/session.py::get_db, which used
to silently roll back every write because it never called session.commit()).

Do NOT point this at a database you care about: every test truncates the
application tables before it runs.
"""

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from alembic import command
from alembic.config import Config
from app.db.session import AsyncSessionLocal, engine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Truncated together via CASCADE, so FK order doesn't strictly matter, but
# listing children-before-parents keeps intent obvious.
_APP_TABLES = [
    "organization_invitations",
    "scoring_rules",
    "assessment_analyses",
    "assessment_transcripts",
    "assessment_recordings",
    "assessment_answers",
    "assessment_sessions",
    "parsed_resumes",
    "resume_files",
    "job_descriptions",
    "candidates",
    "campaigns",
    "users",
    "organizations",
]


@pytest.fixture(scope="session", autouse=True)
def _migrated_schema() -> None:
    """Run real Alembic migrations against the target database once per session."""
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
async def _clean_tables() -> None:
    """
    Truncate before (not after) each test, so a previous run that crashed
    mid-test can't leave stale rows that break uniqueness constraints here.

    Disposes the engine's connection pool first: pytest-asyncio gives each
    test function its own event loop, but asyncpg connections are bound to
    the loop that created them, so a pooled connection from a previous
    test's loop is unusable here and must be dropped rather than reused.
    """
    await engine.dispose()
    async with engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE {', '.join(_APP_TABLES)} RESTART IDENTITY CASCADE")
        )


@pytest.fixture
async def db_session():
    """A fresh session for asserting DB state independently of the API call."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def bootstrapped_admin(client: AsyncClient) -> dict:
    """Bootstrap a fresh organization + ORG_ADMIN via the real API and
    return everything a test needs to act as that admin."""
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "org_name": f"Acme Corp {suffix}",
        "org_slug": f"acme-{suffix}",
        "admin_email": f"admin-{suffix}@example.com",
        "admin_password": "securepass1",
        "admin_full_name": "Admin User",
    }
    res = await client.post("/api/v1/organizations/bootstrap", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    return {
        "org_id": body["organization"]["id"],
        "admin_id": body["admin"]["id"],
        "admin_email": payload["admin_email"],
        "access_token": body["tokens"]["access_token"],
        "headers": {"Authorization": f"Bearer {body['tokens']['access_token']}"},
    }

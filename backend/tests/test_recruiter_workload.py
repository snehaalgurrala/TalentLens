"""
Unit tests for GET /users/recruiter-workload.

Strategy: RecruiterWorkloadService is constructed inside the endpoint (not
injected via a dependency factory), so we mock its constituent repositories
via app.dependency_overrides isn't applicable here — instead we patch
RecruiterWorkloadService.get_workload directly, since the endpoint always
builds a fresh service instance per-request from DBSession.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.main import app
from app.models.resume_file import PipelineStage
from app.models.user import User, UserRole
from app.schemas.recruiter_workload import (
    RecruiterWorkloadItem,
    RecruiterWorkloadResponse,
    RecruiterWorkloadStageBreakdown,
)
from app.schemas.user import UserSummaryResponse

_ORG_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.ORG_ADMIN, org_id: uuid.UUID | None = _ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Test User",
        password_hash="$2b$12$irrelevant",
        role=role,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def org_admin():
    user = make_user(role=UserRole.ORG_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate_role():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestRecruiterWorkload:
    async def test_org_admin_sees_workload(
        self, client_no_lifespan: AsyncClient, org_admin: User
    ):
        recruiter_summary = UserSummaryResponse(
            id=uuid.uuid4(),
            full_name="Jane Recruiter",
            email="jane@example.com",
            role=UserRole.RECRUITER,
        )
        response = RecruiterWorkloadResponse(
            items=[
                RecruiterWorkloadItem(
                    recruiter=recruiter_summary,
                    total_assigned=3,
                    by_stage=[
                        RecruiterWorkloadStageBreakdown(pipeline_stage=PipelineStage.RANKED, count=2),
                        RecruiterWorkloadStageBreakdown(
                            pipeline_stage=PipelineStage.SHORTLISTED, count=1
                        ),
                    ],
                )
            ]
        )
        with patch(
            "app.api.v1.endpoints.users.RecruiterWorkloadService.get_workload",
            new=AsyncMock(return_value=response),
        ):
            res = await client_no_lifespan.get("/api/v1/users/recruiter-workload")

        assert res.status_code == 200
        body = res.json()
        assert body["items"][0]["total_assigned"] == 3
        assert body["items"][0]["recruiter"]["full_name"] == "Jane Recruiter"

    async def test_recruiter_role_forbidden(
        self, client_no_lifespan: AsyncClient, recruiter: User
    ):
        res = await client_no_lifespan.get("/api/v1/users/recruiter-workload")
        assert res.status_code == 403

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, candidate_role: User
    ):
        res = await client_no_lifespan.get("/api/v1/users/recruiter-workload")
        assert res.status_code == 403

    async def test_no_org_returns_422(self, client_no_lifespan: AsyncClient):
        user = make_user(role=UserRole.ORG_ADMIN, org_id=None)
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            with patch(
                "app.api.v1.endpoints.users.RecruiterWorkloadService.get_workload",
                new=AsyncMock(
                    side_effect=HTTPException(422, "You must belong to an organization to view recruiter workload.")
                ),
            ):
                res = await client_no_lifespan.get("/api/v1/users/recruiter-workload")
            assert res.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)

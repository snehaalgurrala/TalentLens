"""
Unit tests for the new pipeline-action endpoints on candidates.py:
  - POST /candidates/{id}/archive, /restore
  - POST /candidates/bulk/archive, /restore, /pipeline-stage

Strategy mirrors test_candidate_management.py: CandidateManagementService is
mocked via dependency override, get_current_user is overridden per-test to
simulate roles.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.candidates import get_candidate_management_service
from app.main import app
from app.models.resume_file import PipelineStage, ReviewStatus, UploadStatus
from app.models.user import User, UserRole
from app.schemas.candidate_management import BulkActionFailure, BulkActionResult
from app.schemas.resume_file import ResumeFileResponse

_ORG_ID = uuid.uuid4()


def make_user(role: UserRole = UserRole.RECRUITER, org_id: uuid.UUID | None = _ORG_ID) -> User:
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


def make_resume_file_response(**overrides) -> ResumeFileResponse:
    defaults = dict(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        original_filename="resume.pdf",
        stored_filename="stored.pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path="path/stored.pdf",
        upload_status=UploadStatus.PARSED,
        uploaded_by=None,
        candidate_id=uuid.uuid4(),
        error_message=None,
        review_status=ReviewStatus.PENDING,
        is_deleted=False,
        uploaded_at=datetime.now(UTC),
        pipeline_stage=PipelineStage.APPLIED,
        assigned_recruiter_id=None,
        notes=None,
    )
    defaults.update(overrides)
    return ResumeFileResponse(**defaults)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_candidate_management_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_candidate_management_service, None)


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


class TestArchive:
    async def test_archives_candidate(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        rf_id = uuid.uuid4()
        mock_service.archive = AsyncMock(
            return_value=make_resume_file_response(id=rf_id, pipeline_stage=PipelineStage.ARCHIVED)
        )
        res = await client_no_lifespan.post(f"/api/v1/candidates/{rf_id}/archive")
        assert res.status_code == 200
        assert res.json()["pipeline_stage"] == "ARCHIVED"

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(f"/api/v1/candidates/{uuid.uuid4()}/archive")
        assert res.status_code == 403
        mock_service.archive.assert_not_called()


class TestRestore:
    async def test_restores_candidate(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        rf_id = uuid.uuid4()
        mock_service.restore = AsyncMock(
            return_value=make_resume_file_response(
                id=rf_id, pipeline_stage=PipelineStage.APPLIED, review_status=ReviewStatus.PENDING
            )
        )
        res = await client_no_lifespan.post(f"/api/v1/candidates/{rf_id}/restore")
        assert res.status_code == 200
        assert res.json()["pipeline_stage"] == "APPLIED"

    async def test_non_terminal_stage_returns_422(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.restore = AsyncMock(
            side_effect=HTTPException(422, "Candidate is not in a terminal stage.")
        )
        res = await client_no_lifespan.post(f"/api/v1/candidates/{uuid.uuid4()}/restore")
        assert res.status_code == 422

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(f"/api/v1/candidates/{uuid.uuid4()}/restore")
        assert res.status_code == 403
        mock_service.restore.assert_not_called()


class TestBulkArchive:
    async def test_bulk_archive_reports_partial_failure(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        ok_id, bad_id = uuid.uuid4(), uuid.uuid4()
        mock_service.bulk_archive = AsyncMock(
            return_value=BulkActionResult(
                succeeded=[ok_id],
                failed=[BulkActionFailure(id=bad_id, reason="Candidate not found.")],
            )
        )
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/archive",
            json={"resume_file_ids": [str(ok_id), str(bad_id)]},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["succeeded"] == [str(ok_id)]
        assert body["failed"][0]["id"] == str(bad_id)

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/archive", json={"resume_file_ids": [str(uuid.uuid4())]}
        )
        assert res.status_code == 403
        mock_service.bulk_archive.assert_not_called()


class TestBulkRestore:
    async def test_bulk_restore(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        ids = [uuid.uuid4(), uuid.uuid4()]
        mock_service.bulk_restore = AsyncMock(
            return_value=BulkActionResult(succeeded=ids, failed=[])
        )
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/restore",
            json={"resume_file_ids": [str(i) for i in ids]},
        )
        assert res.status_code == 200
        assert len(res.json()["succeeded"]) == 2

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/restore", json={"resume_file_ids": [str(uuid.uuid4())]}
        )
        assert res.status_code == 403
        mock_service.bulk_restore.assert_not_called()


class TestBulkPipelineStage:
    async def test_bulk_pipeline_stage_move(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        ids = [uuid.uuid4(), uuid.uuid4()]
        mock_service.bulk_update_pipeline_stage = AsyncMock(
            return_value=BulkActionResult(succeeded=ids, failed=[])
        )
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/pipeline-stage",
            json={"resume_file_ids": [str(i) for i in ids], "pipeline_stage": "INTERVIEW_SCHEDULED"},
        )
        assert res.status_code == 200
        assert len(res.json()["succeeded"]) == 2
        _, kwargs = mock_service.bulk_update_pipeline_stage.call_args
        args, _ = mock_service.bulk_update_pipeline_stage.call_args
        assert args[1] == PipelineStage.INTERVIEW_SCHEDULED

    async def test_missing_pipeline_stage_rejected(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/pipeline-stage",
            json={"resume_file_ids": [str(uuid.uuid4())]},
        )
        assert res.status_code == 422
        mock_service.bulk_update_pipeline_stage.assert_not_called()

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/pipeline-stage",
            json={"resume_file_ids": [str(uuid.uuid4())], "pipeline_stage": "HIRED"},
        )
        assert res.status_code == 403
        mock_service.bulk_update_pipeline_stage.assert_not_called()

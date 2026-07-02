"""
Unit tests for the candidate management endpoints:
  - GET /campaigns/{id}/candidates          (campaigns.py)
  - PATCH/POST /candidates/...              (candidates.py)

Strategy mirrors test_campaigns.py: CandidateManagementService is mocked via
dependency override, get_current_user is overridden per-test to simulate
roles, and RequireRoles runs against the mocked user so role-based 403s are
tested without any service involvement.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.campaigns import (
    get_candidate_management_service as get_campaigns_candidate_service,
)
from app.api.v1.endpoints.candidates import (
    get_candidate_management_service as get_candidates_candidate_service,
)
from app.main import app
from app.models.resume_file import PipelineStage, ReviewStatus, UploadStatus
from app.models.user import User, UserRole
from app.schemas.candidate_management import (
    BulkActionFailure,
    BulkActionResult,
    CandidateListItem,
    CandidateListResponse,
)
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


def make_list_item(**overrides) -> CandidateListItem:
    defaults = dict(
        resume_file_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        candidate_name="Jane Doe",
        email="jane@example.com",
        phone=None,
        location=None,
        current_company="Acme Corp",
        current_role="Engineer",
        years_of_experience=5.0,
        skills=["Python", "SQL"],
        education=[],
        rank=1,
        overall_score=88.0,
        sub_scores=None,
        recommendation="Strong Match",
        upload_status=UploadStatus.PARSED,
        review_status=ReviewStatus.PENDING,
        pipeline_stage=PipelineStage.RANKED,
        assigned_recruiter=None,
        notes=None,
        applied_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return CandidateListItem(**defaults)


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
    app.dependency_overrides[get_campaigns_candidate_service] = lambda: svc
    app.dependency_overrides[get_candidates_candidate_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_campaigns_candidate_service, None)
    app.dependency_overrides.pop(get_candidates_candidate_service, None)


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


# ── List ──────────────────────────────────────────────────────────────────────


class TestListCampaignCandidates:
    def _url(self, campaign_id: uuid.UUID) -> str:
        return f"/api/v1/campaigns/{campaign_id}/candidates"

    async def test_returns_mixed_ranked_and_unranked_rows(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        ranked = make_list_item(overall_score=90.0, pipeline_stage=PipelineStage.RANKED)
        unranked = make_list_item(
            overall_score=None,
            sub_scores=None,
            recommendation=None,
            rank=None,
            upload_status=UploadStatus.PROCESSING,
            pipeline_stage=PipelineStage.PARSING,
        )
        mock_service.list_campaign_candidates = AsyncMock(
            return_value=CandidateListResponse(
                items=[ranked, unranked], total=2, skip=0, limit=50, ranking_available=True
            )
        )

        res = await client_no_lifespan.get(self._url(campaign_id))

        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        assert body["ranking_available"] is True
        assert body["items"][1]["overall_score"] is None
        assert body["items"][1]["pipeline_stage"] == "PARSING"

    async def test_jd_not_ready_returns_empty_scores_not_error(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        campaign_id = uuid.uuid4()
        item = make_list_item(overall_score=None, sub_scores=None, recommendation=None, rank=None)
        mock_service.list_campaign_candidates = AsyncMock(
            return_value=CandidateListResponse(
                items=[item], total=1, skip=0, limit=50, ranking_available=False
            )
        )

        res = await client_no_lifespan.get(self._url(campaign_id))

        assert res.status_code == 200
        body = res.json()
        assert body["ranking_available"] is False
        assert body["items"][0]["overall_score"] is None

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 403

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.list_campaign_candidates = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 404

    async def test_query_params_forwarded(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.list_campaign_candidates = AsyncMock(
            return_value=CandidateListResponse(
                items=[], total=0, skip=10, limit=5, ranking_available=True
            )
        )
        res = await client_no_lifespan.get(
            self._url(uuid.uuid4()),
            params={"search": "python", "skip": 10, "limit": 5, "sort_by": "candidate_name"},
        )
        assert res.status_code == 200
        _, kwargs = mock_service.list_campaign_candidates.call_args
        assert kwargs["search"] == "python"
        assert kwargs["skip"] == 10
        assert kwargs["sort_by"] == "candidate_name"


# ── Single-record actions ────────────────────────────────────────────────────


class TestPipelineStageUpdate:
    async def test_recruiter_can_update(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        rf_id = uuid.uuid4()
        mock_service.update_pipeline_stage = AsyncMock(
            return_value=make_resume_file_response(id=rf_id, pipeline_stage=PipelineStage.SHORTLISTED)
        )
        res = await client_no_lifespan.patch(
            f"/api/v1/candidates/{rf_id}/pipeline-stage", json={"pipeline_stage": "SHORTLISTED"}
        )
        assert res.status_code == 200
        assert res.json()["pipeline_stage"] == "SHORTLISTED"

    async def test_cross_org_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.update_pipeline_stage = AsyncMock(
            side_effect=HTTPException(404, "Candidate not found.")
        )
        res = await client_no_lifespan.patch(
            f"/api/v1/candidates/{uuid.uuid4()}/pipeline-stage", json={"pipeline_stage": "HIRED"}
        )
        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.patch(
            f"/api/v1/candidates/{uuid.uuid4()}/pipeline-stage", json={"pipeline_stage": "HIRED"}
        )
        assert res.status_code == 403


class TestShortlistReject:
    async def test_shortlist(self, client_no_lifespan: AsyncClient, mock_service, recruiter: User):
        rf_id = uuid.uuid4()
        mock_service.shortlist = AsyncMock(
            return_value=make_resume_file_response(id=rf_id, review_status=ReviewStatus.SHORTLISTED)
        )
        res = await client_no_lifespan.post(f"/api/v1/candidates/{rf_id}/shortlist")
        assert res.status_code == 200
        assert res.json()["review_status"] == "SHORTLISTED"

    async def test_reject(self, client_no_lifespan: AsyncClient, mock_service, recruiter: User):
        rf_id = uuid.uuid4()
        mock_service.reject = AsyncMock(
            return_value=make_resume_file_response(id=rf_id, review_status=ReviewStatus.REJECTED)
        )
        res = await client_no_lifespan.post(f"/api/v1/candidates/{rf_id}/reject")
        assert res.status_code == 200
        assert res.json()["review_status"] == "REJECTED"


# ── Bulk actions ──────────────────────────────────────────────────────────────


class TestBulkActions:
    async def test_bulk_shortlist_reports_partial_failure(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        ok_id, bad_id = uuid.uuid4(), uuid.uuid4()
        mock_service.bulk_shortlist = AsyncMock(
            return_value=BulkActionResult(
                succeeded=[ok_id],
                failed=[BulkActionFailure(id=bad_id, reason="Candidate not found.")],
            )
        )
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/shortlist",
            json={"resume_file_ids": [str(ok_id), str(bad_id)]},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["succeeded"] == [str(ok_id)]
        assert body["failed"][0]["id"] == str(bad_id)

    async def test_bulk_delete(self, client_no_lifespan: AsyncClient, mock_service, recruiter: User):
        ids = [uuid.uuid4(), uuid.uuid4()]
        mock_service.bulk_delete = AsyncMock(
            return_value=BulkActionResult(succeeded=ids, failed=[])
        )
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/delete",
            json={"resume_file_ids": [str(i) for i in ids]},
        )
        assert res.status_code == 200
        assert len(res.json()["succeeded"]) == 2

    async def test_bulk_requires_at_least_one_id(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/shortlist", json={"resume_file_ids": []}
        )
        assert res.status_code == 422

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.post(
            "/api/v1/candidates/bulk/shortlist",
            json={"resume_file_ids": [str(uuid.uuid4())]},
        )
        assert res.status_code == 403

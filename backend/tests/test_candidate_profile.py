"""
Unit tests for the candidate profile endpoints:
  - GET /candidates/{id}/profile
  - GET /candidates/{id}/match-analysis

Strategy mirrors test_candidate_management.py: CandidateProfileService is
mocked via dependency override, get_current_user is overridden per-test to
simulate roles, and RequireRoles runs against the mocked user so role-based
403s are tested without any service involvement.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.candidate_profile import get_candidate_profile_service
from app.main import app
from app.models.resume_file import PipelineStage, ReviewStatus, UploadStatus
from app.models.user import User, UserRole
from app.schemas.candidate_profile import (
    CandidateMatchAnalysisResponse,
    CandidateProfileCampaign,
    CandidateProfileResponse,
    StructuredResumeContent,
)
from app.schemas.candidate_ranking import RankingSubScores

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


def make_profile(**overrides) -> CandidateProfileResponse:
    defaults = dict(
        resume_file_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        candidate_name="Jane Doe",
        email="jane@example.com",
        phone=None,
        location=None,
        linkedin_url=None,
        github_url=None,
        current_company="Acme Corp",
        current_role="Engineer",
        years_of_experience=5.0,
        structured_resume=StructuredResumeContent(),
        parse_confidence=0.9,
        campaign=CandidateProfileCampaign(id=uuid.uuid4(), title="Backend Engineer"),
        upload_status=UploadStatus.PARSED,
        review_status=ReviewStatus.PENDING,
        pipeline_stage=PipelineStage.RANKED,
        assigned_recruiter=None,
        uploaded_at=datetime.now(UTC),
        overall_score=88.0,
        sub_scores=RankingSubScores(
            semantic_score=80,
            skills_score=90,
            experience_score=85,
            education_score=100,
            projects_score=70,
            certification_score=60,
        ),
        recommendation="Strong Match",
        ranking_available=True,
    )
    defaults.update(overrides)
    return CandidateProfileResponse(**defaults)


def make_match_analysis(**overrides) -> CandidateMatchAnalysisResponse:
    defaults = dict(
        overall_score=88.0,
        recommendation="Strong Match",
        sub_scores=RankingSubScores(
            semantic_score=80,
            skills_score=90,
            experience_score=85,
            education_score=100,
            projects_score=70,
            certification_score=60,
        ),
        bonus_points=5.0,
        preferred_company_matched=True,
        scoring_rule_source="organization_default",
        match_explanation="Jane Doe scored 88/100 overall (Strong Match).",
        strengths=["Skills: 9/10 required skills matched."],
        weaknesses=["Certifications: 0/2 certification(s) matched."],
        semantic_details={"cosine_similarity": 0.8},
        skills_details={"required": {}, "preferred": {}},
        experience_details={"candidate_years": 5.0, "required_min_years": 3.0},
        education_details={"requirements": []},
        projects_details={"requirements": []},
        certification_details={"required": [], "matched": []},
        explanation_items=[
            {"text": "Excellent Python experience.", "sentiment": "positive", "category": "skills"}
        ],
    )
    defaults.update(overrides)
    return CandidateMatchAnalysisResponse(**defaults)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_candidate_profile_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_candidate_profile_service, None)


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


class TestGetCandidateProfile:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/profile"

    async def test_returns_profile(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        candidate_id = uuid.uuid4()
        profile = make_profile(candidate_id=candidate_id)
        mock_service.get_profile = AsyncMock(return_value=profile)

        res = await client_no_lifespan.get(self._url(candidate_id))

        assert res.status_code == 200
        body = res.json()
        assert body["candidate_name"] == "Jane Doe"
        assert body["overall_score"] == 88.0
        assert body["ranking_available"] is True

    async def test_not_yet_ranked_has_null_scores(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        candidate_id = uuid.uuid4()
        profile = make_profile(
            overall_score=None, sub_scores=None, recommendation=None, ranking_available=False
        )
        mock_service.get_profile = AsyncMock(return_value=profile)

        res = await client_no_lifespan.get(self._url(candidate_id))

        assert res.status_code == 200
        body = res.json()
        assert body["overall_score"] is None
        assert body["ranking_available"] is False

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.get_profile = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Candidate not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_profile.assert_not_called()


class TestGetCandidateMatchAnalysis:
    def _url(self, id_: uuid.UUID) -> str:
        return f"/api/v1/candidates/{id_}/match-analysis"

    async def test_returns_match_analysis(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        candidate_id = uuid.uuid4()
        analysis = make_match_analysis()
        mock_service.get_match_analysis = AsyncMock(return_value=analysis)

        res = await client_no_lifespan.get(self._url(candidate_id))

        assert res.status_code == 200
        body = res.json()
        assert body["overall_score"] == 88.0
        assert body["bonus_points"] == 5.0
        assert body["preferred_company_matched"] is True
        assert body["explanation_items"][0]["sentiment"] == "positive"

    async def test_not_yet_ranked_returns_422(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        mock_service.get_match_analysis = AsyncMock(
            side_effect=HTTPException(status_code=422, detail="This candidate has not been ranked yet.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 422

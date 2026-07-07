"""
Unit tests for the assessment analysis read endpoint:
  - GET /assessment/analysis/{transcript_id}

Strategy mirrors test_assessment_transcripts.py: AssessmentAnalysisService is
mocked via dependency override; RBAC is exercised against the CANDIDATE role.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.assessment_analysis import get_assessment_analysis_service
from app.main import app
from app.models.assessment_analysis import AnalysisStatus, AnalysisType, AssessmentAnalysis
from app.models.user import User, UserRole

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


def make_analysis(**overrides) -> AssessmentAnalysis:
    now = datetime.now(UTC)
    defaults = dict(
        id=overrides.get("id", uuid.uuid4()),
        organization_id=_ORG_ID,
        transcript_id=overrides.get("transcript_id", uuid.uuid4()),
        analysis_type=overrides.get("analysis_type", AnalysisType.READ_ALOUD),
        status=overrides.get("status", AnalysisStatus.PENDING),
        overall_score=overrides.get("overall_score"),
        word_accuracy=overrides.get("word_accuracy"),
        correct_words=overrides.get("correct_words"),
        missing_words=overrides.get("missing_words"),
        extra_words=overrides.get("extra_words"),
        substituted_words=overrides.get("substituted_words"),
        total_words=overrides.get("total_words"),
        reading_speed_wpm=overrides.get("reading_speed_wpm"),
        completion_percentage=overrides.get("completion_percentage"),
        semantic_similarity=overrides.get("semantic_similarity"),
        keyword_coverage=overrides.get("keyword_coverage"),
        analysis_json=overrides.get("analysis_json"),
        error_message=overrides.get("error_message"),
        created_at=now,
        updated_at=now,
    )
    return AssessmentAnalysis(**defaults)


@pytest.fixture
def mock_service():
    svc = MagicMock()
    app.dependency_overrides[get_assessment_analysis_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_assessment_analysis_service, None)


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


class TestGetAssessmentAnalysis:
    def _url(self, transcript_id: uuid.UUID) -> str:
        return f"/api/v1/assessment/analysis/{transcript_id}"

    async def test_returns_completed_analysis(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        analysis = make_analysis(
            status=AnalysisStatus.COMPLETED,
            overall_score=91.5,
            word_accuracy=95.0,
            correct_words=19,
            missing_words=1,
            extra_words=0,
            substituted_words=0,
            total_words=20,
            reading_speed_wpm=120.0,
            completion_percentage=95.0,
            analysis_json={"correct_words": ["the"], "missing_words": ["fox"]},
        )
        mock_service.get_analysis = AsyncMock(return_value=analysis)

        res = await client_no_lifespan.get(self._url(analysis.transcript_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "COMPLETED"
        assert body["analysis_type"] == "READ_ALOUD"
        assert body["overall_score"] == 91.5
        assert body["word_accuracy"] == 95.0
        assert body["total_words"] == 20
        assert body["analysis_json"] == {"correct_words": ["the"], "missing_words": ["fox"]}

    async def test_returns_completed_listen_repeat_analysis(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        analysis = make_analysis(
            analysis_type=AnalysisType.LISTEN_REPEAT,
            status=AnalysisStatus.COMPLETED,
            overall_score=88.0,
            completion_percentage=100.0,
            semantic_similarity=92.0,
            keyword_coverage=80.0,
            analysis_json={"matched_keywords": ["innovation"], "missing_keywords": []},
        )
        mock_service.get_analysis = AsyncMock(return_value=analysis)

        res = await client_no_lifespan.get(self._url(analysis.transcript_id))

        assert res.status_code == 200
        body = res.json()
        assert body["analysis_type"] == "LISTEN_REPEAT"
        assert body["semantic_similarity"] == 92.0
        assert body["keyword_coverage"] == 80.0
        assert body["word_accuracy"] is None

    async def test_returns_pending_analysis_with_null_fields(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        analysis = make_analysis(status=AnalysisStatus.PENDING)
        mock_service.get_analysis = AsyncMock(return_value=analysis)

        res = await client_no_lifespan.get(self._url(analysis.transcript_id))

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "PENDING"
        assert body["overall_score"] is None

    async def test_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_service, recruiter: User
    ):
        from fastapi import HTTPException

        mock_service.get_analysis = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Analysis not found.")
        )

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 404

    async def test_candidate_role_forbidden(
        self, client_no_lifespan: AsyncClient, mock_service, candidate_role: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 403
        mock_service.get_analysis.assert_not_called()

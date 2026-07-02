"""
Unit tests for the candidate-ranking endpoint.

Strategy (mirrors tests/test_campaigns.py and tests/test_scoring_rules.py):
  - get_candidate_ranking_service is overridden with a MagicMock — no database required.
  - get_current_user is overridden per-test to simulate different roles.
"""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints.rankings import get_candidate_ranking_service
from app.main import app
from app.models.user import User, UserRole
from app.services.candidate_ranking import CandidateRankingEntry
from app.services.matching_service import MatchResult, ScoreExplanation

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


def _match_result() -> MatchResult:
    explanations = {
        name: ScoreExplanation(score=90.0, weight=0.1, summary=f"{name} summary.", details={})
        for name in ("semantic", "skills", "experience", "education", "projects", "certification")
    }
    explanations["overall"] = ScoreExplanation(score=90.0, weight=1.0, summary="Overall summary.", details={})
    return MatchResult(
        overall_score=90,
        semantic_score=90,
        skills_score=90,
        experience_score=90,
        education_score=90,
        projects_score=90,
        certification_score=90,
        explanations=explanations,
    )


def make_entry(**overrides) -> CandidateRankingEntry:
    defaults = dict(
        rank=1,
        candidate_id=uuid.uuid4(),
        candidate_name="Jane Doe",
        resume_file_id=uuid.uuid4(),
        overall_score=90.0,
        match_result=_match_result(),
        recommendation="Strong Match",
        strengths=["Skills: matched."],
        weaknesses=[],
        match_explanation="Jane Doe scored 90/100 overall (Strong Match).",
        scoring_rule_source="system_default",
    )
    defaults.update(overrides)
    return CandidateRankingEntry(**defaults)


@pytest.fixture
def mock_ranking_service():
    svc = MagicMock()
    app.dependency_overrides[get_candidate_ranking_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_candidate_ranking_service, None)


@pytest.fixture
def recruiter():
    user = make_user(role=UserRole.RECRUITER)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def org_admin():
    user = make_user(role=UserRole.ORG_ADMIN)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def candidate():
    user = make_user(role=UserRole.CANDIDATE)
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestRankCampaignCandidates:
    def _url(self, campaign_id: uuid.UUID) -> str:
        return f"/api/v1/campaigns/{campaign_id}/rankings"

    async def test_recruiter_can_view_rankings(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        entries = [
            make_entry(rank=1),
            make_entry(rank=2, overall_score=60.0, recommendation="Possible Match"),
        ]
        mock_ranking_service.rank_campaign = AsyncMock(return_value=entries)

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.status_code == 200
        body = res.json()
        assert len(body) == 2
        assert body[0]["rank"] == 1
        assert body[0]["sub_scores"]["semantic_score"] == 90
        assert body[1]["overall_score"] == 60.0
        assert body[1]["recommendation"] == "Possible Match"

    async def test_org_admin_can_view_rankings(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, org_admin: User
    ):
        mock_ranking_service.rank_campaign = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 200
        assert res.json() == []

    async def test_candidate_cannot_view_rankings(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, candidate: User
    ):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 403

    async def test_unauthenticated_returns_401(self, client_no_lifespan: AsyncClient):
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 401

    async def test_campaign_not_found_returns_404(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        mock_ranking_service.rank_campaign = AsyncMock(
            side_effect=HTTPException(404, "Campaign not found.")
        )
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 404

    async def test_no_ready_job_description_returns_422(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        mock_ranking_service.rank_campaign = AsyncMock(
            side_effect=HTTPException(
                422,
                "This campaign has no job description that has finished parsing "
                "and embedding yet, so candidates cannot be ranked.",
            )
        )
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 422

    async def test_empty_campaign_returns_empty_list(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        mock_ranking_service.rank_campaign = AsyncMock(return_value=[])
        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        assert res.status_code == 200
        assert res.json() == []

    async def test_response_includes_strengths_weaknesses_and_explanation(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        entry = make_entry(
            strengths=["Skills: matched all required skills."],
            weaknesses=["Education: no requirements matched."],
            match_explanation="Detailed explanation of the match.",
        )
        mock_ranking_service.rank_campaign = AsyncMock(return_value=[entry])

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        body = res.json()[0]

        assert body["strengths"] == ["Skills: matched all required skills."]
        assert body["weaknesses"] == ["Education: no requirements matched."]
        assert body["match_explanation"] == "Detailed explanation of the match."

    async def test_response_ordering_is_preserved_from_service(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        entries = [
            make_entry(rank=1, candidate_name="Amy Adams"),
            make_entry(rank=2, candidate_name="Zed Zephyr"),
        ]
        mock_ranking_service.rank_campaign = AsyncMock(return_value=entries)

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))
        body = res.json()

        assert [b["candidate_name"] for b in body] == ["Amy Adams", "Zed Zephyr"]

    async def test_scoring_rule_source_is_included(
        self, client_no_lifespan: AsyncClient, mock_ranking_service, recruiter: User
    ):
        entry = make_entry(scoring_rule_source="campaign_override")
        mock_ranking_service.rank_campaign = AsyncMock(return_value=[entry])

        res = await client_no_lifespan.get(self._url(uuid.uuid4()))

        assert res.json()[0]["scoring_rule_source"] == "campaign_override"

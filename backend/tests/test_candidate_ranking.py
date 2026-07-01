"""
Unit tests for app.services.candidate_ranking.CandidateRankingService.

Repositories and ScoringRuleService are mocked (AsyncMock) — no database.
Resume/JD/Candidate rows are built with the real SQLAlchemy model classes
(matching tests/test_scoring_rules.py's convention) so attribute access in
the service under test behaves exactly as it would against real ORM rows.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.campaign import Campaign, CampaignStatus
from app.models.candidate import Candidate
from app.models.embedding import EmbeddingStatus
from app.models.job_description import JobDescription, ParsingStatus
from app.models.parsed_resume import ParsedResume
from app.models.resume_file import ResumeFile, UploadStatus
from app.models.user import User, UserRole
from app.schemas.scoring_rule import SYSTEM_DEFAULT_WEIGHTS, EffectiveScoringRuleResponse
from app.services.candidate_ranking import CandidateRankingService, RankingThresholds
from app.services.matching_service import MatchResult, ScoreExplanation

_ORG_ID = uuid.uuid4()
_CAMPAIGN_ID = uuid.uuid4()

_RESUME_JSON = {
    "candidate": {
        "first_name": "Jane",
        "last_name": "Doe",
        "years_of_experience": 5.0,
        "current_role": "Engineer",
        "current_company": "Acme Corp",
    },
    "structured_resume": {
        "skills": ["Python", "SQL", "FastAPI"],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "summary": "Backend engineer.",
    },
    "confidence": 0.9,
}

_WEAK_RESUME_JSON = {
    "candidate": {
        "first_name": "Bob",
        "last_name": "Smith",
        "years_of_experience": 1.0,
        "current_role": "Marketer",
        "current_company": "Other Inc",
    },
    "structured_resume": {
        "skills": ["Marketing"],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "summary": "Marketing generalist.",
    },
    "confidence": 0.9,
}

_JD_JSON = {
    "job": {
        "title": "Backend Engineer",
        "experience_min": 3,
        "experience_max": 6,
        "industry": "",
        "employment_type": "Full-time",
        "location": "Remote",
    },
    "structured_jd": {
        "required_skills": ["Python", "SQL"],
        "preferred_skills": ["FastAPI"],
        "education": [],
        "projects": [],
        "responsibilities": [],
        "certifications": [],
    },
    "confidence": 0.9,
}


# ── Fixture builders ────────────────────────────────────────────────────────


def make_user(role: UserRole = UserRole.RECRUITER, org_id=_ORG_ID) -> User:
    return User(
        id=uuid.uuid4(),
        email="rec@example.com",
        full_name="Recruiter",
        password_hash="x",
        role=role,
        org_id=org_id,
        is_active=True,
        refresh_token_hash=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def make_campaign(**overrides) -> Campaign:
    campaign = Campaign(
        id=_CAMPAIGN_ID,
        org_id=_ORG_ID,
        created_by=uuid.uuid4(),
        title="Backend Hiring",
        description=None,
        status=CampaignStatus.ACTIVE,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        object.__setattr__(campaign, k, v)
    return campaign


def make_job_description(**overrides) -> JobDescription:
    jd = JobDescription(
        id=uuid.uuid4(),
        campaign_id=_CAMPAIGN_ID,
        created_by=None,
        original_filename=None,
        raw_text="We need a backend engineer.",
        structured_json=_JD_JSON,
        parser_version="v1",
        parsed_at=datetime.now(timezone.utc),
        parsing_status=ParsingStatus.COMPLETED,
        parsing_error=None,
        embedding_status=EmbeddingStatus.READY,
        embedding_model="local",
        embedding_generated_at=datetime.now(timezone.utc),
        embedding=[1.0, 0.0],
        embedding_dimension=2,
        is_deleted=False,
        deleted_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        object.__setattr__(jd, k, v)
    return jd


def make_resume_file(candidate_id=None, **overrides) -> ResumeFile:
    rf = ResumeFile(
        id=uuid.uuid4(),
        campaign_id=_CAMPAIGN_ID,
        original_filename="resume.pdf",
        stored_filename="stored.pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path="/tmp/stored.pdf",
        upload_status=UploadStatus.PARSED,
        uploaded_by=None,
        is_deleted=False,
        deleted_at=None,
        uploaded_at=datetime.now(timezone.utc),
        candidate_id=candidate_id or uuid.uuid4(),
        error_message=None,
    )
    for k, v in overrides.items():
        object.__setattr__(rf, k, v)
    return rf


def make_parsed_resume(resume_file_id, structured_json=None, embedding=None, **overrides) -> ParsedResume:
    pr = ParsedResume(
        id=uuid.uuid4(),
        resume_file_id=resume_file_id,
        candidate_id=uuid.uuid4(),
        raw_text="resume text",
        structured_json=structured_json or _RESUME_JSON,
        parser_version="v1",
        parsed_at=datetime.now(timezone.utc),
        embedding_status=EmbeddingStatus.READY,
        embedding_model="local",
        embedding_generated_at=datetime.now(timezone.utc),
        embedding=embedding if embedding is not None else [1.0, 0.0],
        embedding_dimension=2,
    )
    for k, v in overrides.items():
        object.__setattr__(pr, k, v)
    return pr


def make_candidate(**overrides) -> Candidate:
    candidate = Candidate(
        id=uuid.uuid4(),
        organization_id=_ORG_ID,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone=None,
        linkedin_url=None,
        github_url=None,
        location=None,
        years_of_experience=5.0,
        current_company="Acme Corp",
        current_role="Engineer",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    for k, v in overrides.items():
        object.__setattr__(candidate, k, v)
    return candidate


def make_effective_rule(**overrides) -> EffectiveScoringRuleResponse:
    payload = {
        "id": None,
        "org_id": _ORG_ID,
        "campaign_id": _CAMPAIGN_ID,
        "created_by": None,
        **SYSTEM_DEFAULT_WEIGHTS,
        "preferred_company_bonus": 0.0,
        "preferred_companies": [],
        "source": "system_default",
        "created_at": None,
        "updated_at": None,
    }
    payload.update(overrides)
    return EffectiveScoringRuleResponse(**payload)


def _match_result(**score_overrides) -> MatchResult:
    scores = {
        "semantic": 90.0,
        "skills": 80.0,
        "experience": 60.0,
        "education": 40.0,
        "projects": 20.0,
        "certification": 95.0,
    }
    scores.update(score_overrides)
    explanations = {
        name: ScoreExplanation(score=value, weight=0.1, summary=f"{name} summary ({value:.0f}).", details={})
        for name, value in scores.items()
    }
    explanations["overall"] = ScoreExplanation(score=70.0, weight=1.0, summary="Weighted overall summary.", details={})
    return MatchResult(
        overall_score=70,
        semantic_score=round(scores["semantic"]),
        skills_score=round(scores["skills"]),
        experience_score=round(scores["experience"]),
        education_score=round(scores["education"]),
        projects_score=round(scores["projects"]),
        certification_score=round(scores["certification"]),
        explanations=explanations,
    )


def _build_service(
    *,
    campaign=None,
    job_descriptions=None,
    resume_files=None,
    parsed_resumes=None,
    candidates=None,
    effective_rule=None,
    thresholds=None,
) -> CandidateRankingService:
    campaign_repo = MagicMock()
    campaign_repo.get_by_id = AsyncMock(return_value=campaign if campaign is not None else make_campaign())

    job_description_repo = MagicMock()
    job_description_repo.list_by_campaign = AsyncMock(
        return_value=job_descriptions if job_descriptions is not None else [make_job_description()]
    )

    resume_file_repo = MagicMock()
    resume_file_repo.list_by_campaign = AsyncMock(return_value=resume_files if resume_files is not None else [])

    parsed_resume_repo = MagicMock()
    parsed_resume_repo.list_by_resume_file_ids = AsyncMock(
        return_value=parsed_resumes if parsed_resumes is not None else []
    )

    candidate_repo = MagicMock()
    candidate_repo.list_by_ids = AsyncMock(return_value=candidates if candidates is not None else [])

    scoring_rule_service = MagicMock()
    scoring_rule_service.get_effective = AsyncMock(
        return_value=effective_rule if effective_rule is not None else make_effective_rule()
    )

    return CandidateRankingService(
        campaign_repo=campaign_repo,
        resume_file_repo=resume_file_repo,
        parsed_resume_repo=parsed_resume_repo,
        candidate_repo=candidate_repo,
        job_description_repo=job_description_repo,
        scoring_rule_service=scoring_rule_service,
        thresholds=thresholds,
    )


def _wire_one_candidate(service: CandidateRankingService, *, resume_json, embedding, candidate_overrides=None):
    """Helper: wires a single fully-ready resume/candidate through the mocked repos."""
    resume_file = make_resume_file()
    parsed_resume = make_parsed_resume(resume_file.id, structured_json=resume_json, embedding=embedding)
    candidate = make_candidate(id=resume_file.candidate_id, **(candidate_overrides or {}))
    service.resume_file_repo.list_by_campaign = AsyncMock(return_value=[resume_file])
    service.parsed_resume_repo.list_by_resume_file_ids = AsyncMock(return_value=[parsed_resume])
    service.candidate_repo.list_by_ids = AsyncMock(return_value=[candidate])
    return resume_file, parsed_resume, candidate


# ── Validation / guard tests ─────────────────────────────────────────────────


class TestRankCampaignValidation:
    async def test_user_without_org_raises_422(self):
        service = _build_service()
        user = make_user(org_id=None)
        with pytest.raises(HTTPException) as exc:
            await service.rank_campaign(_CAMPAIGN_ID, user)
        assert exc.value.status_code == 422

    async def test_campaign_not_found_raises_404(self):
        service = _build_service(campaign=None)
        service.campaign_repo.get_by_id = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert exc.value.status_code == 404

    async def test_no_job_descriptions_raises_422(self):
        service = _build_service(job_descriptions=[])
        with pytest.raises(HTTPException) as exc:
            await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert exc.value.status_code == 422

    async def test_job_description_not_parsed_raises_422(self):
        jd = make_job_description(parsing_status=ParsingStatus.PROCESSING)
        service = _build_service(job_descriptions=[jd])
        with pytest.raises(HTTPException) as exc:
            await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert exc.value.status_code == 422

    async def test_job_description_embedding_not_ready_raises_422(self):
        jd = make_job_description(embedding_status=EmbeddingStatus.PENDING)
        service = _build_service(job_descriptions=[jd])
        with pytest.raises(HTTPException) as exc:
            await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert exc.value.status_code == 422

    async def test_picks_first_ready_job_description_when_multiple(self):
        not_ready = make_job_description(parsing_status=ParsingStatus.PROCESSING)
        ready = make_job_description()
        service = _build_service(job_descriptions=[not_ready, ready])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []  # no resumes wired, but no exception means a ready JD was found

    async def test_no_resume_files_returns_empty_list(self):
        service = _build_service(resume_files=[])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []


# ── Filtering: which resumes are eligible ────────────────────────────────────


class TestEligibilityFiltering:
    async def test_skips_resume_not_yet_parsed(self):
        rf = make_resume_file(upload_status=UploadStatus.PROCESSING)
        service = _build_service(resume_files=[rf])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []

    async def test_skips_resume_without_candidate_id(self):
        rf = make_resume_file()
        object.__setattr__(rf, "candidate_id", None)
        service = _build_service(resume_files=[rf])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []

    async def test_skips_when_parsed_resume_missing(self):
        rf = make_resume_file()
        service = _build_service(resume_files=[rf], parsed_resumes=[])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []

    async def test_skips_parsed_resume_with_embedding_not_ready(self):
        rf = make_resume_file()
        pr = make_parsed_resume(rf.id, embedding_status=EmbeddingStatus.GENERATING)
        service = _build_service(resume_files=[rf], parsed_resumes=[pr])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []

    async def test_skips_when_candidate_record_missing(self):
        rf = make_resume_file()
        pr = make_parsed_resume(rf.id)
        service = _build_service(resume_files=[rf], parsed_resumes=[pr], candidates=[])
        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())
        assert result == []


# ── Full ranking behavior ────────────────────────────────────────────────────


class TestRankCampaignScoring:
    async def test_strong_candidate_is_ranked_first_with_strong_match(self):
        service = _build_service()
        resume_file, _, candidate = _wire_one_candidate(
            service, resume_json=_RESUME_JSON, embedding=[1.0, 0.0]
        )

        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())

        assert len(result) == 1
        entry = result[0]
        assert entry.rank == 1
        assert entry.candidate_id == candidate.id
        assert entry.candidate_name == "Jane Doe"
        assert entry.resume_file_id == resume_file.id
        assert entry.overall_score == 100.0
        assert entry.recommendation == "Strong Match"
        assert entry.scoring_rule_source == "system_default"

    async def test_weak_candidate_scores_lower_and_is_not_a_strong_match(self):
        service = _build_service()
        _wire_one_candidate(
            service,
            resume_json=_WEAK_RESUME_JSON,
            embedding=[0.0, 1.0],  # orthogonal to the JD embedding [1, 0]
            candidate_overrides={"current_company": "Other Inc"},
        )

        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())

        assert len(result) == 1
        entry = result[0]
        assert entry.overall_score < 70.0
        assert entry.recommendation in {"Possible Match", "Not a Match"}

    async def test_higher_scoring_candidate_is_ranked_first(self):
        strong_rf = make_resume_file()
        strong_pr = make_parsed_resume(strong_rf.id, structured_json=_RESUME_JSON, embedding=[1.0, 0.0])
        strong_candidate = make_candidate(id=strong_rf.candidate_id, first_name="Aaron")

        weak_rf = make_resume_file()
        weak_pr = make_parsed_resume(weak_rf.id, structured_json=_WEAK_RESUME_JSON, embedding=[0.0, 1.0])
        weak_candidate = make_candidate(id=weak_rf.candidate_id, first_name="Zack", current_company="Other Inc")

        service = _build_service(
            resume_files=[weak_rf, strong_rf],  # deliberately out of expected-rank order
            parsed_resumes=[weak_pr, strong_pr],
            candidates=[weak_candidate, strong_candidate],
        )

        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())

        assert [e.candidate_id for e in result] == [strong_candidate.id, weak_candidate.id]
        assert [e.rank for e in result] == [1, 2]

    async def test_ties_are_broken_alphabetically_by_name(self):
        rf_a = make_resume_file()
        pr_a = make_parsed_resume(rf_a.id, structured_json=_RESUME_JSON, embedding=[1.0, 0.0])
        candidate_a = make_candidate(id=rf_a.candidate_id, first_name="Zed", last_name="Zephyr")

        rf_b = make_resume_file()
        pr_b = make_parsed_resume(rf_b.id, structured_json=_RESUME_JSON, embedding=[1.0, 0.0])
        candidate_b = make_candidate(id=rf_b.candidate_id, first_name="Amy", last_name="Adams")

        service = _build_service(
            resume_files=[rf_a, rf_b],
            parsed_resumes=[pr_a, pr_b],
            candidates=[candidate_a, candidate_b],
        )

        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())

        assert [e.candidate_name for e in result] == ["Amy Adams", "Zed Zephyr"]

    async def test_preferred_company_bonus_reflected_in_score_and_explanation(self):
        rule = make_effective_rule(
            preferred_company_bonus=0.05,
            preferred_companies=["Acme Corp"],
            source="organization_default",
        )
        service = _build_service(effective_rule=rule)
        _wire_one_candidate(
            service,
            resume_json=_RESUME_JSON,
            embedding=[1.0, 0.0],
            candidate_overrides={"current_company": "Acme Corp"},
        )

        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())

        entry = result[0]
        assert entry.overall_score == 100.0  # already at 100, bonus clamps rather than overflows
        assert any("Preferred employer" in s for s in entry.strengths)
        assert "bonus" in entry.match_explanation.lower()
        assert entry.scoring_rule_source == "organization_default"

    async def test_scoring_rule_source_is_propagated(self):
        rule = make_effective_rule(source="campaign_override")
        service = _build_service(effective_rule=rule)
        _wire_one_candidate(service, resume_json=_RESUME_JSON, embedding=[1.0, 0.0])

        result = await service.rank_campaign(_CAMPAIGN_ID, make_user())

        assert result[0].scoring_rule_source == "campaign_override"
        assert "campaign-specific" in result[0].match_explanation


# ── Pure helper methods ──────────────────────────────────────────────────────


class TestRecommendationThresholds:
    def test_boundaries(self):
        service = _build_service()
        assert service._recommendation(85.0) == "Strong Match"
        assert service._recommendation(84.9) == "Good Match"
        assert service._recommendation(70.0) == "Good Match"
        assert service._recommendation(69.9) == "Possible Match"
        assert service._recommendation(50.0) == "Possible Match"
        assert service._recommendation(49.9) == "Not a Match"
        assert service._recommendation(0.0) == "Not a Match"

    def test_custom_thresholds_are_respected(self):
        service = _build_service(thresholds=RankingThresholds(strong_match=95.0))
        assert service._recommendation(90.0) == "Good Match"
        assert service._recommendation(95.0) == "Strong Match"


class TestStrengthsAndWeaknesses:
    def test_buckets_by_default_thresholds(self):
        service = _build_service()
        match_result = _match_result(
            semantic=90.0, skills=80.0, experience=60.0, education=40.0, projects=20.0, certification=95.0
        )

        strengths, weaknesses = service._strengths_and_weaknesses(match_result)

        assert any(s.startswith("Semantic fit:") for s in strengths)
        assert any(s.startswith("Skills:") for s in strengths)
        assert any(s.startswith("Certifications:") for s in strengths)
        assert any(w.startswith("Education:") for w in weaknesses)
        assert any(w.startswith("Projects:") for w in weaknesses)
        # experience (60) is between the weakness (50) and strength (75) thresholds -> neutral
        assert not any("Experience:" in s for s in strengths + weaknesses)

    def test_all_high_scores_yield_no_weaknesses(self):
        service = _build_service()
        match_result = _match_result(
            semantic=100.0, skills=100.0, experience=100.0, education=100.0, projects=100.0, certification=100.0
        )
        strengths, weaknesses = service._strengths_and_weaknesses(match_result)
        assert len(strengths) == 6
        assert weaknesses == []

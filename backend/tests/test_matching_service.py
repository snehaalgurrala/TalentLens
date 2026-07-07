"""
Unit tests for app.services.matching_service.

No database, no HTTP, no AI calls — MatchingService is pure computation over
plain data. Resume/JobDescription rows are stood in with SimpleNamespace
objects exposing just `.structured_json`, matching the attribute-only access
the service actually performs.
"""

from types import SimpleNamespace

import pytest

from app.services.matching_service import (
    MatchingService,
    MatchingWeights,
    MatchResult,
    ScoreExplanation,
    _best_match_ratio,
    _normalize_skill,
    _token_overlap_ratio,
    _tokenize,
    cosine_similarity,
)

# ── Fixture builders ────────────────────────────────────────────────────────


def _resume_json(
    *,
    skills=None,
    years_of_experience=5.0,
    current_role="Software Engineer",
    current_company="Acme Corp",
    summary="Backend engineer with distributed systems experience.",
    experience=None,
    education=None,
    projects=None,
    certifications=None,
) -> dict:
    return {
        "candidate": {
            "first_name": "Alice",
            "last_name": "Smith",
            "years_of_experience": years_of_experience,
            "current_role": current_role,
            "current_company": current_company,
        },
        "structured_resume": {
            "skills": skills if skills is not None else ["Python", "SQL", "FastAPI"],
            "experience": experience or [],
            "education": education or [],
            "projects": projects or [],
            "certifications": certifications or [],
            "summary": summary,
        },
        "confidence": 0.9,
    }


def _jd_json(
    *,
    required_skills=None,
    preferred_skills=None,
    experience_min=3,
    experience_max=6,
    industry="",
    education=None,
    projects=None,
    certifications=None,
) -> dict:
    return {
        "job": {
            "title": "Backend Engineer",
            "experience_min": experience_min,
            "experience_max": experience_max,
            "industry": industry,
            "employment_type": "Full-time",
            "location": "Remote",
        },
        "structured_jd": {
            "required_skills": required_skills if required_skills is not None else ["Python", "SQL"],
            "preferred_skills": preferred_skills if preferred_skills is not None else ["FastAPI"],
            "education": education or [],
            "projects": projects or [],
            "responsibilities": [],
            "certifications": certifications or [],
        },
        "confidence": 0.9,
    }


def _resume(**kwargs) -> SimpleNamespace:
    return SimpleNamespace(structured_json=_resume_json(**kwargs))


def _jd(**kwargs) -> SimpleNamespace:
    return SimpleNamespace(structured_json=_jd_json(**kwargs))


# ── cosine_similarity ──────────────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_vectors_returns_one(self):
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors_returns_zero(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors_returns_negative_one(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_mismatched_dimensions_raises(self):
        with pytest.raises(ValueError, match="dimension mismatch"):
            cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0])

    def test_numpy_float32_inputs_return_native_python_float(self):
        """Regression: pgvector decodes embedding columns as numpy.float32
        elements. round(numpy.float32, 4) silently stays numpy.float32,
        which Pydantic can't serialize -- this crashed the match-analysis
        endpoint for every candidate. cosine_similarity must always hand
        back a native float regardless of the input element type."""
        import numpy as np

        result = cosine_similarity(
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
            np.array([1.0, 2.0, 3.0], dtype=np.float32),
        )
        assert type(result) is float
        assert round(result, 4) == pytest.approx(1.0)


# ── text-matching primitives ───────────────────────────────────────────────


class TestTokenize:
    def test_lowercases_and_splits(self):
        assert _tokenize("Python SQL") == {"python", "sql"}

    def test_drops_stopwords_and_single_chars(self):
        assert _tokenize("a Bachelor of Science") == {"bachelor", "science"}

    def test_empty_string(self):
        assert _tokenize("") == set()


class TestNormalizeSkill:
    def test_strips_punctuation_and_lowercases(self):
        assert _normalize_skill("Node.js") == _normalize_skill("node-js") == _normalize_skill("NodeJS")

    def test_distinct_words_stay_distinct(self):
        assert _normalize_skill("Python") != _normalize_skill("SQL")


class TestTokenOverlapRatio:
    def test_full_overlap(self):
        assert _token_overlap_ratio("Python SQL", "Expert in Python and SQL") == pytest.approx(1.0)

    def test_no_overlap(self):
        assert _token_overlap_ratio("Python", "Marketing strategy") == 0.0

    def test_partial_overlap(self):
        # "computer science" -> {"computer", "science"}; only "science" present in b
        assert _token_overlap_ratio("computer science", "data science team") == pytest.approx(0.5)

    def test_empty_target_returns_zero(self):
        assert _token_overlap_ratio("", "anything") == 0.0


class TestBestMatchRatio:
    def test_picks_best_of_several_candidates(self):
        ratio = _best_match_ratio("Python SQL", ["irrelevant", "Python and SQL expert"])
        assert ratio == pytest.approx(1.0)

    def test_empty_candidates_returns_zero(self):
        assert _best_match_ratio("Python", []) == 0.0


# ── MatchingService — validation ───────────────────────────────────────────


class TestMatchingServiceValidation:
    def test_missing_resume_structured_json_raises(self):
        svc = MatchingService()
        resume = SimpleNamespace(structured_json=None)
        jd = _jd()
        with pytest.raises(ValueError, match="resume.structured_json"):
            svc.calculate_match(resume, jd, [1.0], [1.0])

    def test_missing_jd_structured_json_raises(self):
        svc = MatchingService()
        resume = _resume()
        jd = SimpleNamespace(structured_json=None)
        with pytest.raises(ValueError, match="job_description.structured_json"):
            svc.calculate_match(resume, jd, [1.0], [1.0])

    def test_empty_resume_embedding_raises(self):
        svc = MatchingService()
        with pytest.raises(ValueError, match="embedding"):
            svc.calculate_match(_resume(), _jd(), [], [1.0])

    def test_empty_jd_embedding_raises(self):
        svc = MatchingService()
        with pytest.raises(ValueError, match="embedding"):
            svc.calculate_match(_resume(), _jd(), [1.0], [])

    def test_mismatched_embedding_dimensions_raises(self):
        svc = MatchingService()
        with pytest.raises(ValueError, match="dimension mismatch"):
            svc.calculate_match(_resume(), _jd(), [1.0, 2.0, 3.0], [1.0, 2.0])


# ── MatchingService — end-to-end scoring ───────────────────────────────────


class TestMatchingServiceScoring:
    def test_perfect_match_scores_100_across_the_board(self):
        svc = MatchingService()
        resume = _resume(skills=["Python", "SQL", "FastAPI"], years_of_experience=5.0)
        jd = _jd(
            required_skills=["Python", "SQL"],
            preferred_skills=["FastAPI"],
            experience_min=3,
            experience_max=6,
            industry="",  # no requirement -> neutral
        )

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.semantic_score == 100
        assert result.skills_score == 100
        assert result.experience_score == 100
        assert result.education_score == 100  # no requirement -> neutral
        assert result.projects_score == 100
        assert result.certification_score == 100
        assert result.overall_score == 100
        # Regression: the "no certifications required" branch must still
        # populate "missing" (empty), since ExplainableMatchingService reads
        # details["missing"] unconditionally and previously raised KeyError
        # whenever a JD had no certification requirements.
        assert result.explanations["certification"].details["missing"] == []

    def test_partial_skill_match(self):
        svc = MatchingService()
        resume = _resume(skills=["Python"])
        jd = _jd(required_skills=["Python", "SQL"], preferred_skills=["FastAPI"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        # required_coverage=0.5*0.7 + preferred_coverage=0.0*0.3 = 0.35 -> 35
        assert result.skills_score == 35

    def test_no_skill_requirements_is_neutral(self):
        svc = MatchingService()
        resume = _resume(skills=[])
        jd = _jd(required_skills=[], preferred_skills=[])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.skills_score == 100

    def test_synonym_skill_match_scores_below_exact(self):
        svc = MatchingService()
        resume = _resume(skills=["JavaScript"])
        jd = _jd(required_skills=["JS"], preferred_skills=[])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        # required_coverage = synonym_skill_credit(0.9) -> (0.9*0.7 + 1.0*0.3)*100 = 93
        assert result.skills_score == 93
        details = result.explanations["skills"].details["required"]
        assert details["synonym_matches"] == [{"skill": "JS", "matched_to": "JavaScript"}]
        assert details["exact_matches"] == []

    def test_experience_below_minimum_scales_proportionally(self):
        svc = MatchingService()
        resume = _resume(years_of_experience=1.5)
        jd = _jd(experience_min=3, experience_max=6)

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.experience_score == 50  # 1.5 / 3 = 0.5

    def test_experience_meeting_minimum_is_full_score_even_if_above_max(self):
        svc = MatchingService()
        resume = _resume(years_of_experience=20.0)
        jd = _jd(experience_min=3, experience_max=6)

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.experience_score == 100

    def test_no_experience_requirement_is_neutral(self):
        svc = MatchingService()
        resume = _resume(years_of_experience=0.0)
        jd = _jd(experience_min=0, experience_max=0)

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.experience_score == 100

    def test_education_degree_and_field_both_match(self):
        svc = MatchingService()
        resume = _resume(
            education=[
                {"institution": "MIT", "degree": "Bachelor of Science", "field": "Computer Science"}
            ]
        )
        jd = _jd(education=["B.Sc. Computer Science"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.education_score == 100

    def test_no_education_on_file_scores_zero(self):
        svc = MatchingService()
        resume = _resume(education=[])
        jd = _jd(education=["PhD in Physics"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.education_score == 0

    def test_certification_match(self):
        svc = MatchingService()
        resume = _resume(certifications=[{"name": "AWS Certified Developer", "issuer": "Amazon"}])
        jd = _jd(certifications=["AWS Certified Developer"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.certification_score == 100

    def test_project_technology_and_description_both_match(self):
        svc = MatchingService()
        resume = _resume(
            projects=[
                {
                    "name": "Payments Rewrite",
                    "description": "Rebuilt the payments platform",
                    "technologies": ["Python", "Kafka"],
                }
            ]
        )
        jd = _jd(projects=["Payments platform rewrite using Python and Kafka"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.projects_score == 100

    def test_project_technology_mismatch_scores_partial_credit(self):
        svc = MatchingService()
        resume = _resume(
            projects=[
                {
                    "name": "Payments Rewrite",
                    "description": "Rebuilt the payments platform",
                    "technologies": ["Python"],
                }
            ]
        )
        # requirement text never names a technology, so only the description overlaps
        jd = _jd(projects=["Payments platform rewrite"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        # tech_credit=0 (no tech named in requirement) * 0.6 + desc_credit=1.0 * 0.4 = 0.4 -> 40
        assert result.projects_score == 40

    def test_no_candidate_projects_scores_zero(self):
        svc = MatchingService()
        resume = _resume(projects=[])
        jd = _jd(projects=["Payments platform rewrite"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.projects_score == 0

    def test_domain_relevance_affects_semantic_score(self):
        svc = MatchingService()
        matching_resume = _resume(
            current_role="Fintech Engineer", summary="Built fintech payment systems."
        )
        unrelated_resume = _resume(current_role="Gardener", summary="Landscaping expert.")
        jd = _jd(industry="Fintech")

        matching_result = svc.calculate_match(matching_resume, jd, [1.0, 0.0], [1.0, 0.0])
        unrelated_result = svc.calculate_match(unrelated_resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert matching_result.semantic_score > unrelated_result.semantic_score

    def test_orthogonal_embeddings_lower_semantic_score_than_identical(self):
        svc = MatchingService()
        resume = _resume()
        jd = _jd()

        identical = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])
        orthogonal = svc.calculate_match(resume, jd, [1.0, 0.0], [0.0, 1.0])

        assert identical.semantic_score > orthogonal.semantic_score


# ── MatchingService — skill match tiers (exact / synonym / partial) ────────


class TestSkillClassification:
    def test_exact_match_ignores_case_and_punctuation(self):
        svc = MatchingService()
        tier, credit, matched = svc._classify_skill("node.js", ["NodeJS"])
        assert tier == "exact"
        assert credit == 1.0
        assert matched == "NodeJS"

    def test_synonym_match_uses_configured_credit(self):
        svc = MatchingService()
        tier, credit, matched = svc._classify_skill("K8s", ["Kubernetes"])
        assert tier == "synonym"
        assert credit == svc.weights.synonym_skill_credit
        assert matched == "Kubernetes"

    def test_partial_match_scales_by_overlap_ratio(self):
        svc = MatchingService()
        tier, credit, matched = svc._classify_skill("Kubernetes", ["Kubernetes Administration"])
        assert tier == "partial"
        assert credit == pytest.approx(svc.weights.partial_skill_credit_scale * 1.0)
        assert matched == "Kubernetes Administration"

    def test_below_partial_threshold_is_no_match(self):
        svc = MatchingService()
        tier, credit, matched = svc._classify_skill("Rust", ["Python"])
        assert tier == "none"
        assert credit == 0.0
        assert matched is None

    def test_custom_synonym_map_is_respected(self):
        weights = MatchingWeights(skill_synonyms={"react": ["reactjs", "front-end react"]})
        svc = MatchingService(weights=weights)
        tier, _credit, matched = svc._classify_skill("React", ["front-end React"])
        assert tier == "synonym"
        assert matched == "front-end React"

    def test_required_skill_isolated_weight_applies_partial_credit(self):
        weights = MatchingWeights(required_skill_weight=1.0, preferred_skill_weight=0.0)
        svc = MatchingService(weights=weights)
        resume = _resume(skills=["Kubernetes Administration"])
        jd = _jd(required_skills=["Kubernetes"], preferred_skills=["ignored"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        # partial credit = partial_skill_credit_scale(0.75) * ratio(1.0) = 0.75 -> 75
        assert result.skills_score == 75


# ── MatchingService — education degree/field scoring ────────────────────────


class TestEducationRequirementScoring:
    def test_higher_candidate_degree_meets_lower_requirement(self):
        svc = MatchingService()
        candidates = [{"institution": "MIT", "degree": "PhD in Computer Science", "field": "Computer Science"}]
        result = svc._score_education_requirement("Bachelor's degree in Computer Science", candidates)
        assert result["best_match"]["degree_credit"] == 1.0

    def test_lower_candidate_degree_gets_proportional_credit(self):
        svc = MatchingService()
        candidates = [{"institution": "MIT", "degree": "MBA", "field": "Business"}]
        result = svc._score_education_requirement("PhD in Physics", candidates)
        # cand_rank(3) / req_rank(4)
        assert result["best_match"]["degree_credit"] == pytest.approx(0.75)

    def test_unrelated_field_scores_zero_field_credit(self):
        svc = MatchingService()
        candidates = [
            {"institution": "MIT", "degree": "Master of Science", "field": "Business Administration"}
        ]
        result = svc._score_education_requirement("Master's degree in Physics", candidates)
        assert result["best_match"]["degree_credit"] == 1.0
        assert result["best_match"]["field_credit"] == 0.0

    def test_no_degree_requirement_gives_full_degree_credit(self):
        svc = MatchingService()
        candidates = [{"institution": "MIT", "degree": "", "field": "Computer Science"}]
        result = svc._score_education_requirement("Strong Computer Science background", candidates)
        assert result["required_degree_rank"] is None
        assert result["best_match"]["degree_credit"] == 1.0

    def test_extract_degree_rank(self):
        svc = MatchingService()
        assert svc._extract_degree_rank("PhD in Physics") == 4
        assert svc._extract_degree_rank("B.Sc. Computer Science") == 2
        assert svc._extract_degree_rank("Diploma in Welding") == 1
        assert svc._extract_degree_rank("Strong communicator") is None


# ── MatchingWeights — configurability ───────────────────────────────────────


class TestConfigurableWeights:
    def test_overall_score_uses_custom_weights(self):
        weights = MatchingWeights(
            semantic_weight=1.0,
            skills_weight=0.0,
            experience_weight=0.0,
            education_weight=0.0,
            projects_weight=0.0,
            certification_weight=0.0,
        )
        svc = MatchingService(weights=weights)
        resume = _resume(skills=[])  # would tank skills_score under default weights
        jd = _jd(required_skills=["Something totally unmatched"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        # Only semantic_weight is nonzero, so overall == semantic regardless of skills_score.
        assert result.overall_score == result.semantic_score

    def test_skill_weight_favors_required_over_preferred(self):
        weights = MatchingWeights(required_skill_weight=1.0, preferred_skill_weight=0.0)
        svc = MatchingService(weights=weights)
        resume = _resume(skills=["Python", "SQL"])  # matches required only
        jd = _jd(required_skills=["Python", "SQL"], preferred_skills=["Rust"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.skills_score == 100  # preferred_skill_weight=0 means missing Rust doesn't matter

    def test_default_weights_are_used_when_none_passed(self):
        svc = MatchingService()
        assert svc.weights.semantic_weight == 0.30

    def test_coverage_match_threshold_is_configurable(self):
        lenient_weights = MatchingWeights(coverage_match_threshold=0.3)
        strict_weights = MatchingWeights(coverage_match_threshold=0.99)
        resume = _resume(
            certifications=[{"name": "AWS Certified Developer - Associate", "issuer": "Amazon"}]
        )
        jd = _jd(certifications=["AWS Certified Developer Professional"])

        lenient_result = MatchingService(weights=lenient_weights).calculate_match(
            resume, jd, [1.0, 0.0], [1.0, 0.0]
        )
        strict_result = MatchingService(weights=strict_weights).calculate_match(
            resume, jd, [1.0, 0.0], [1.0, 0.0]
        )

        assert lenient_result.certification_score == 100
        assert strict_result.certification_score == 0

    def test_partial_skill_match_threshold_is_configurable(self):
        strict_weights = MatchingWeights(partial_skill_match_threshold=0.99)
        svc = MatchingService(weights=strict_weights)
        # overlap ratio for this pair is 0.75 (3 of the 4 requirement tokens
        # are covered) — under the default 0.6 threshold that's "partial",
        # but a strict 0.99 threshold rejects it.
        tier, _credit, _matched = svc._classify_skill(
            "Kubernetes Cluster Autoscaling Management", ["Kubernetes Cluster Autoscaling"]
        )
        assert tier == "none"

    def test_education_degree_weight_is_configurable(self):
        weights = MatchingWeights(education_degree_weight=1.0, education_field_weight=0.0)
        svc = MatchingService(weights=weights)
        candidates = [{"institution": "MIT", "degree": "MBA", "field": "Unrelated Field"}]
        result = svc._score_education_requirement("PhD in Physics", candidates)
        assert result["credit"] == pytest.approx(0.75)  # field_weight=0 means field mismatch doesn't matter

    def test_project_technology_weight_is_configurable(self):
        weights = MatchingWeights(project_technology_weight=1.0, project_description_weight=0.0)
        svc = MatchingService(weights=weights)
        resume = _resume(
            projects=[{"name": "X", "description": "Unrelated text", "technologies": ["Python"]}]
        )
        jd = _jd(projects=["Built a service in Python"])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])

        assert result.projects_score == 100  # description_weight=0, tech match alone is full credit


# ── Result shape / explanations ─────────────────────────────────────────────


class TestResultShape:
    def test_scores_returns_exact_expected_keys(self):
        svc = MatchingService()
        result = svc.calculate_match(_resume(), _jd(), [1.0, 0.0], [1.0, 0.0])

        assert set(result.scores().keys()) == {
            "overall_score",
            "semantic_score",
            "skills_score",
            "experience_score",
            "education_score",
            "projects_score",
            "certification_score",
        }
        assert all(isinstance(v, int) for v in result.scores().values())

    def test_explanations_cover_every_score(self):
        svc = MatchingService()
        result = svc.calculate_match(_resume(), _jd(), [1.0, 0.0], [1.0, 0.0])

        assert set(result.explanations.keys()) == {
            "overall",
            "semantic",
            "skills",
            "experience",
            "education",
            "projects",
            "certification",
        }
        for expl in result.explanations.values():
            assert isinstance(expl, ScoreExplanation)
            d = expl.to_dict()
            assert set(d.keys()) == {"score", "weight", "summary", "details"}
            assert isinstance(d["summary"], str) and d["summary"]

    def test_skill_explanation_details_list_matched_and_missing(self):
        svc = MatchingService()
        resume = _resume(skills=["Python"])
        jd = _jd(required_skills=["Python", "SQL"], preferred_skills=[])

        result = svc.calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])
        details = result.explanations["skills"].details["required"]

        assert details["exact_matches"] == ["Python"]
        assert details["missing"] == ["SQL"]

    def test_to_dict_matches_documented_contract_shape(self):
        svc = MatchingService()
        result = svc.calculate_match(_resume(), _jd(), [1.0, 0.0], [1.0, 0.0])
        d = result.to_dict()

        for key in (
            "overall_score",
            "semantic_score",
            "skills_score",
            "experience_score",
            "education_score",
            "projects_score",
            "certification_score",
        ):
            assert key in d
        assert "explanations" in d
        assert isinstance(d["explanations"], dict)

    def test_isinstance_match_result(self):
        svc = MatchingService()
        result = svc.calculate_match(_resume(), _jd(), [1.0, 0.0], [1.0, 0.0])
        assert isinstance(result, MatchResult)

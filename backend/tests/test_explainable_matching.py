"""
Unit tests for app.services.explainable_matching.ExplainableMatchingService.

Two layers:
  - TestGoldenExampleScenario runs the real MatchingService end-to-end on a
    crafted resume/JD pair and asserts the exact bullet strings from the
    feature spec come out the other end.
  - Everything else builds MatchResult objects directly (via the _match_result
    helper) so each category's threshold/cap behavior can be tested in
    isolation, the same way tests/test_candidate_ranking.py tests
    _strengths_and_weaknesses without going through a full match.
"""
from types import SimpleNamespace

from app.services.explainable_matching import (
    DEFAULT_THRESHOLDS,
    ExplainableMatchingService,
    ExplanationThresholds,
)
from app.services.matching_service import MatchingService, MatchResult, ScoreExplanation

# ── MatchResult builder for isolated category tests ─────────────────────────

_BASE_DETAILS = {
    "semantic": {
        "cosine_similarity": 1.0,
        "cosine_score": 100.0,
        "domain_relevance_score": 100.0,
        "cosine_weight": 0.8,
        "domain_weight": 0.2,
        "industry": None,
    },
    "skills": {
        "required": {
            "skills": [],
            "exact_matches": [],
            "synonym_matches": [],
            "partial_matches": [],
            "missing": [],
        },
        "preferred": {
            "skills": [],
            "exact_matches": [],
            "synonym_matches": [],
            "partial_matches": [],
            "missing": [],
        },
        "required_skill_weight": 0.7,
        "preferred_skill_weight": 0.3,
    },
    "experience": {"candidate_years": 0.0, "required_min_years": 0.0, "required_max_years": 0.0},
    "education": {"requirements": []},
    "projects": {"requirements": []},
    "certification": {"required": [], "matched": [], "missing": []},
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _match_result(scores: dict[str, float] | None = None, details: dict[str, dict] | None = None) -> MatchResult:
    merged_details = {k: dict(v) for k, v in _BASE_DETAILS.items()}
    for category, override in (details or {}).items():
        merged_details[category] = _deep_merge(merged_details[category], override)

    merged_scores = {name: 100.0 for name in _BASE_DETAILS}
    merged_scores.update(scores or {})

    explanations = {
        name: ScoreExplanation(score=merged_scores[name], weight=0.1, summary=f"{name} summary.", details=merged_details[name])
        for name in _BASE_DETAILS
    }
    explanations["overall"] = ScoreExplanation(score=100.0, weight=1.0, summary="Overall summary.", details={})

    return MatchResult(
        overall_score=100,
        semantic_score=round(merged_scores["semantic"]),
        skills_score=round(merged_scores["skills"]),
        experience_score=round(merged_scores["experience"]),
        education_score=round(merged_scores["education"]),
        projects_score=round(merged_scores["projects"]),
        certification_score=round(merged_scores["certification"]),
        explanations=explanations,
    )


# ── Golden example: full pipeline, exact bullet strings from the spec ──────


class TestGoldenExampleScenario:
    def test_produces_the_specified_example_bullets(self):
        resume = SimpleNamespace(
            structured_json={
                "candidate": {
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "years_of_experience": 6.0,
                    "current_role": "Backend Engineer",
                    "current_company": "TechCo",
                },
                "structured_resume": {
                    "skills": ["Python", "Django", "PostgreSQL"],
                    "experience": [],
                    "education": [
                        {
                            "institution": "State University",
                            "degree": "Bachelor of Science",
                            "field": "Computer Science",
                        }
                    ],
                    "projects": [],
                    "certifications": [],
                    "summary": "Experienced backend development engineer building scalable Python services.",
                },
                "confidence": 0.9,
            }
        )
        jd = SimpleNamespace(
            structured_json={
                "job": {
                    "title": "Backend Engineer",
                    "experience_min": 3,
                    "experience_max": 6,
                    "industry": "Backend Development",
                    "employment_type": "Full-time",
                    "location": "Remote",
                },
                "structured_jd": {
                    "required_skills": ["Python", "Kubernetes"],
                    "preferred_skills": [],
                    "education": ["B.Sc. Computer Science"],
                    "projects": [],
                    "responsibilities": [],
                    "certifications": ["AWS"],
                },
                "confidence": 0.9,
            }
        )

        match_result = MatchingService().calculate_match(resume, jd, [1.0, 0.0], [1.0, 0.0])
        bullets = ExplainableMatchingService().explain_as_text(match_result)

        assert "Excellent Python experience." in bullets
        assert "Strong Backend Development background." in bullets
        assert "Missing Kubernetes experience." in bullets
        assert "Education fully satisfies JD." in bullets
        assert "AWS certification preferred but not present." in bullets

    def test_no_llm_or_network_dependency(self):
        """ExplainableMatchingService only imports stdlib + MatchingService's
        pure dataclasses — this test documents that guarantee by checking the
        module has no httpx/requests/openai/anthropic-style imports."""
        import app.services.explainable_matching as module

        source = module.__file__
        with open(source, encoding="utf-8") as f:
            content = f.read()
        for forbidden in ("httpx", "requests", "openai", "anthropic", "urllib"):
            assert forbidden not in content


# ── Skills ────────────────────────────────────────────────────────────────


class TestSkillExplanations:
    def test_exact_match_phrasing(self):
        result = _match_result(
            details={"skills": {"required": {"exact_matches": ["Python"], "missing": []}}}
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Excellent Python experience." in bullets

    def test_synonym_match_phrasing(self):
        result = _match_result(
            details={
                "skills": {
                    "required": {
                        "synonym_matches": [{"skill": "K8s", "matched_to": "Kubernetes"}],
                    }
                }
            }
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Solid K8s experience (via Kubernetes)." in bullets

    def test_partial_match_phrasing(self):
        result = _match_result(
            details={
                "skills": {
                    "required": {
                        "partial_matches": [{"skill": "Kubernetes", "matched_to": "Kubernetes Administration"}],
                    }
                }
            }
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Some Kubernetes experience (partial match with Kubernetes Administration)." in bullets

    def test_missing_required_skill_phrasing(self):
        result = _match_result(details={"skills": {"required": {"missing": ["Kubernetes"]}}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Missing Kubernetes experience." in bullets

    def test_missing_required_skills_are_never_truncated(self):
        missing = [f"Skill{i}" for i in range(10)]
        result = _match_result(details={"skills": {"required": {"missing": missing}}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        for skill in missing:
            assert f"Missing {skill} experience." in bullets

    def test_exact_matches_are_capped(self):
        matches = [f"Skill{i}" for i in range(10)]
        result = _match_result(details={"skills": {"required": {"exact_matches": matches}}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        excellent_bullets = [b for b in bullets if b.startswith("Excellent")]
        assert len(excellent_bullets) == DEFAULT_THRESHOLDS.max_exact_skill_highlights

    def test_preferred_matched_and_missing_phrasing(self):
        result = _match_result(
            details={
                "skills": {
                    "preferred": {
                        "exact_matches": ["FastAPI"],
                        "missing": ["GraphQL"],
                    }
                }
            }
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Bonus: FastAPI experience (preferred)." in bullets
        assert "GraphQL preferred but not present." in bullets


# ── Experience ────────────────────────────────────────────────────────────


class TestExperienceExplanations:
    def test_no_requirement_produces_no_bullet(self):
        result = _match_result(details={"experience": {"candidate_years": 5.0, "required_min_years": 0.0}})
        items = ExplainableMatchingService().explain(result)
        assert not any(i.category == "experience" for i in items)

    def test_strong_margin_is_positive(self):
        result = _match_result(details={"experience": {"candidate_years": 10.0, "required_min_years": 3.0}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Strong experience: 10 years (requirement: 3+)." in bullets

    def test_meets_requirement_exactly_is_positive_but_not_strong(self):
        result = _match_result(details={"experience": {"candidate_years": 3.5, "required_min_years": 3.0}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Meets experience requirement: 3.5 years vs 3+ required." in bullets

    def test_below_requirement_is_negative(self):
        result = _match_result(details={"experience": {"candidate_years": 1.0, "required_min_years": 3.0}})
        items = ExplainableMatchingService().explain(result)
        exp_items = [i for i in items if i.category == "experience"]
        assert len(exp_items) == 1
        assert exp_items[0].sentiment == "negative"
        assert "Below required experience" in exp_items[0].text


# ── Domain / semantic ─────────────────────────────────────────────────────


class TestDomainExplanations:
    def test_no_industry_produces_no_bullet(self):
        result = _match_result(details={"semantic": {"industry": None, "domain_relevance_score": 100.0}})
        items = ExplainableMatchingService().explain(result)
        assert not any(i.category == "semantic" for i in items)

    def test_strong_relevance_phrasing(self):
        result = _match_result(
            details={"semantic": {"industry": "Fintech", "domain_relevance_score": 80.0}}
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Strong Fintech background." in bullets

    def test_weak_relevance_phrasing(self):
        result = _match_result(
            details={"semantic": {"industry": "Fintech", "domain_relevance_score": 10.0}}
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Limited Fintech background evident from the resume." in bullets

    def test_middling_relevance_produces_no_bullet(self):
        result = _match_result(
            details={"semantic": {"industry": "Fintech", "domain_relevance_score": 45.0}}
        )
        items = ExplainableMatchingService().explain(result)
        assert not any(i.category == "semantic" for i in items)


# ── Education ──────────────────────────────────────────────────────────────


class TestEducationExplanations:
    def test_no_requirements_produces_no_bullet(self):
        result = _match_result(details={"education": {"requirements": []}})
        items = ExplainableMatchingService().explain(result)
        assert not any(i.category == "education" for i in items)

    def test_full_match_phrasing(self):
        result = _match_result(
            scores={"education": 100.0},
            details={"education": {"requirements": [{"requirement": "B.Sc. CS", "credit": 1.0}]}},
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Education fully satisfies JD." in bullets

    def test_no_match_phrasing(self):
        result = _match_result(
            scores={"education": 0.0},
            details={"education": {"requirements": [{"requirement": "PhD Physics", "credit": 0.0}]}},
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Education does not meet JD requirements." in bullets

    def test_partial_match_phrasing(self):
        result = _match_result(
            scores={"education": 50.0},
            details={
                "education": {
                    "requirements": [
                        {"requirement": "B.Sc. CS", "credit": 1.0},
                        {"requirement": "MBA", "credit": 0.0},
                    ]
                }
            },
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Education partially satisfies JD (1/2 requirement(s) met)." in bullets


# ── Projects ──────────────────────────────────────────────────────────────


class TestProjectExplanations:
    def test_no_requirements_produces_no_bullets(self):
        result = _match_result(details={"projects": {"requirements": []}})
        items = ExplainableMatchingService().explain(result)
        assert not any(i.category == "projects" for i in items)

    def test_relevant_project_phrasing(self):
        result = _match_result(
            details={"projects": {"requirements": [{"requirement": "Payments platform rewrite", "credit": 0.8}]}}
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "Relevant project experience: Payments platform rewrite." in bullets

    def test_no_matching_project_phrasing(self):
        result = _match_result(
            details={"projects": {"requirements": [{"requirement": "ML recommendation engine", "credit": 0.0}]}}
        )
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "No project experience matching 'ML recommendation engine'." in bullets

    def test_project_highlights_are_capped(self):
        requirements = [{"requirement": f"Project {i}", "credit": 0.8} for i in range(10)]
        result = _match_result(details={"projects": {"requirements": requirements}})
        items = ExplainableMatchingService().explain(result)
        project_items = [i for i in items if i.category == "projects"]
        assert len(project_items) == DEFAULT_THRESHOLDS.max_project_highlights


# ── Certifications ────────────────────────────────────────────────────────


class TestCertificationExplanations:
    def test_matched_certification_phrasing(self):
        result = _match_result(details={"certification": {"matched": ["AWS Certified Developer"]}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "AWS Certified Developer certification confirmed." in bullets

    def test_missing_certification_phrasing(self):
        result = _match_result(details={"certification": {"missing": ["AWS"]}})
        bullets = ExplainableMatchingService().explain_as_text(result)
        assert "AWS certification preferred but not present." in bullets


# ── explain() vs explain_as_text() ──────────────────────────────────────────


class TestExplainReturnShapes:
    def test_explain_returns_items_with_sentiment_and_category(self):
        result = _match_result(details={"skills": {"required": {"exact_matches": ["Python"]}}})
        items = ExplainableMatchingService().explain(result)
        python_item = next(i for i in items if "Python" in i.text)
        assert python_item.sentiment == "positive"
        assert python_item.category == "skills"

    def test_explain_as_text_returns_plain_strings_in_same_order(self):
        result = _match_result(details={"skills": {"required": {"exact_matches": ["Python"]}}})
        service = ExplainableMatchingService()
        items = service.explain(result)
        texts = service.explain_as_text(result)
        assert texts == [i.text for i in items]


# ── Configurable thresholds ──────────────────────────────────────────────────


class TestConfigurableThresholds:
    def test_custom_cap_truncates_exact_matches(self):
        service = ExplainableMatchingService(thresholds=ExplanationThresholds(max_exact_skill_highlights=1))
        result = _match_result(details={"skills": {"required": {"exact_matches": ["Python", "SQL", "Go"]}}})
        bullets = service.explain_as_text(result)
        assert len([b for b in bullets if b.startswith("Excellent")]) == 1

    def test_stricter_domain_threshold_changes_bucket(self):
        service = ExplainableMatchingService(thresholds=ExplanationThresholds(strong_domain_relevance=90.0))
        result = _match_result(details={"semantic": {"industry": "Fintech", "domain_relevance_score": 80.0}})
        items = service.explain(result)
        # 80 no longer clears the raised 90 bar, and the (default) weak
        # threshold of 25 isn't triggered either -> neutral, no bullet.
        assert not any(i.category == "semantic" for i in items)

    def test_custom_experience_margin(self):
        service = ExplainableMatchingService(thresholds=ExplanationThresholds(strong_experience_margin=2.0))
        result = _match_result(details={"experience": {"candidate_years": 5.0, "required_min_years": 3.0}})
        bullets = service.explain_as_text(result)
        # margin is 1.67, below the raised 2.0 bar -> "meets" not "strong"
        assert any(b.startswith("Meets experience requirement") for b in bullets)
        assert not any(b.startswith("Strong experience") for b in bullets)

"""
Unit tests for app.schemas.scoring_rule (weight-sum / bonus-cap validation)
and app.services.scoring_rule.compute_final_score.

Pure logic only — no database, no HTTP. compute_final_score is exercised
against SimpleNamespace stand-ins so the "hard cap regardless of what the
rule claims" behavior can be tested even with an out-of-range value that
the Pydantic schema itself would never allow through.
"""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.scoring_rule import (
    MAX_PREFERRED_COMPANY_BONUS,
    SYSTEM_DEFAULT_WEIGHTS,
    ScoringRuleCreate,
    ScoringRuleUpdate,
)
from app.services.scoring_rule import compute_final_score

# ── Fixture builder ─────────────────────────────────────────────────────────


def _rule(**overrides) -> SimpleNamespace:
    defaults = {
        "semantic_weight": 0.30,
        "skills_weight": 0.25,
        "experience_weight": 0.15,
        "education_weight": 0.10,
        "project_weight": 0.10,
        "certification_weight": 0.10,
        "preferred_company_bonus": 0.0,
        "preferred_companies": [],
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


_SCORES = dict(
    semantic_score=90.0,
    skills_score=80.0,
    experience_score=100.0,
    education_score=70.0,
    project_score=60.0,
    certification_score=50.0,
)


# ── ScoringRuleCreate — weight sum / bonus cap ──────────────────────────────


class TestScoringRuleCreateValidation:
    def test_defaults_sum_to_one_and_are_accepted(self):
        rule = ScoringRuleCreate()
        assert rule.semantic_weight == SYSTEM_DEFAULT_WEIGHTS["semantic_weight"]
        assert rule.preferred_company_bonus == 0.0
        assert rule.preferred_companies == []

    def test_valid_weights_summing_to_one_are_accepted(self):
        rule = ScoringRuleCreate(
            semantic_weight=0.4,
            skills_weight=0.2,
            experience_weight=0.2,
            education_weight=0.1,
            project_weight=0.05,
            certification_weight=0.05,
        )
        assert sum(
            (
                rule.semantic_weight,
                rule.skills_weight,
                rule.experience_weight,
                rule.education_weight,
                rule.project_weight,
                rule.certification_weight,
            )
        ) == pytest.approx(1.0)

    def test_weights_not_summing_to_one_are_rejected(self):
        with pytest.raises(ValidationError, match="must sum to 1.0"):
            ScoringRuleCreate(
                semantic_weight=0.5,
                skills_weight=0.5,
                experience_weight=0.5,
                education_weight=0.0,
                project_weight=0.0,
                certification_weight=0.0,
            )

    def test_preferred_company_bonus_at_max_is_accepted(self):
        rule = ScoringRuleCreate(preferred_company_bonus=MAX_PREFERRED_COMPANY_BONUS)
        assert rule.preferred_company_bonus == MAX_PREFERRED_COMPANY_BONUS

    def test_preferred_company_bonus_over_max_is_rejected(self):
        with pytest.raises(ValidationError):
            ScoringRuleCreate(preferred_company_bonus=MAX_PREFERRED_COMPANY_BONUS + 0.01)

    def test_negative_bonus_is_rejected(self):
        with pytest.raises(ValidationError):
            ScoringRuleCreate(preferred_company_bonus=-0.01)

    def test_negative_weight_is_rejected(self):
        with pytest.raises(ValidationError):
            ScoringRuleCreate(semantic_weight=-0.1, skills_weight=1.1)

    def test_preferred_companies_defaults_are_independent_lists(self):
        # A shared mutable default would leak state across instances.
        a = ScoringRuleCreate()
        b = ScoringRuleCreate()
        a.preferred_companies.append("Acme")
        assert b.preferred_companies == []


# ── ScoringRuleUpdate — partial update rules ────────────────────────────────


class TestScoringRuleUpdateValidation:
    def test_no_fields_provided_is_valid(self):
        update = ScoringRuleUpdate()
        assert update.model_dump(exclude_unset=True) == {}

    def test_non_weight_field_alone_is_valid(self):
        update = ScoringRuleUpdate(preferred_companies=["Acme Corp"])
        assert update.preferred_companies == ["Acme Corp"]

    def test_all_six_weights_summing_to_one_is_valid(self):
        update = ScoringRuleUpdate(
            semantic_weight=0.5,
            skills_weight=0.2,
            experience_weight=0.1,
            education_weight=0.1,
            project_weight=0.05,
            certification_weight=0.05,
        )
        assert update.semantic_weight == 0.5

    def test_all_six_weights_not_summing_to_one_is_rejected(self):
        with pytest.raises(ValidationError, match="must sum to 1.0"):
            ScoringRuleUpdate(
                semantic_weight=0.9,
                skills_weight=0.9,
                experience_weight=0.0,
                education_weight=0.0,
                project_weight=0.0,
                certification_weight=0.0,
            )

    def test_partial_weight_subset_is_rejected(self):
        with pytest.raises(ValidationError, match="all six weight fields"):
            ScoringRuleUpdate(semantic_weight=0.5, skills_weight=0.5)

    def test_bonus_over_max_is_rejected(self):
        with pytest.raises(ValidationError):
            ScoringRuleUpdate(preferred_company_bonus=0.06)


# ── compute_final_score ──────────────────────────────────────────────────────


class TestComputeFinalScore:
    def test_weighted_average_with_no_bonus(self):
        score = compute_final_score(_rule(), **_SCORES)
        # 90*.3 + 80*.25 + 100*.15 + 70*.1 + 60*.1 + 50*.1 = 27+20+15+7+6+5 = 80
        assert score == pytest.approx(80.0)

    def test_bonus_applied_when_candidate_company_is_preferred(self):
        rule = _rule(preferred_company_bonus=0.05, preferred_companies=["Google", "Meta"])
        score = compute_final_score(rule, **_SCORES, candidate_company="google")
        assert score == pytest.approx(85.0)  # 80 + 5 points

    def test_bonus_matching_is_case_and_whitespace_insensitive(self):
        rule = _rule(preferred_company_bonus=0.05, preferred_companies=[" Google "])
        score = compute_final_score(rule, **_SCORES, candidate_company="GOOGLE")
        assert score == pytest.approx(85.0)

    def test_no_bonus_when_company_not_preferred(self):
        rule = _rule(preferred_company_bonus=0.05, preferred_companies=["Google"])
        score = compute_final_score(rule, **_SCORES, candidate_company="Amazon")
        assert score == pytest.approx(80.0)

    def test_no_bonus_when_candidate_company_is_none(self):
        rule = _rule(preferred_company_bonus=0.05, preferred_companies=["Google"])
        score = compute_final_score(rule, **_SCORES, candidate_company=None)
        assert score == pytest.approx(80.0)

    def test_bonus_is_hard_capped_regardless_of_rule_value(self):
        # Bypasses the Pydantic schema entirely to prove compute_final_score
        # itself enforces the 5% ceiling as defense in depth.
        rule = _rule(preferred_company_bonus=0.50, preferred_companies=["Foo"])
        score = compute_final_score(rule, **_SCORES, candidate_company="Foo")
        assert score == pytest.approx(85.0)  # capped at +5, not +50

    def test_final_score_clamped_to_100(self):
        rule = _rule(
            semantic_weight=1.0,
            skills_weight=0.0,
            experience_weight=0.0,
            education_weight=0.0,
            project_weight=0.0,
            certification_weight=0.0,
            preferred_company_bonus=0.05,
            preferred_companies=["Google"],
        )
        scores = {**_SCORES, "semantic_score": 100.0}
        score = compute_final_score(rule, **scores, candidate_company="Google")
        assert score == 100.0

    def test_final_score_clamped_to_zero(self):
        rule = _rule()
        scores = {k: 0.0 for k in _SCORES}
        score = compute_final_score(rule, **scores)
        assert score == 0.0

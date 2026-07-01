"""
ExplainableMatchingService — turns a MatchResult (already computed by
MatchingService) into short, recruiter-friendly explanation bullets, e.g.:

    Excellent Python experience.
    Strong Backend Development background.
    Missing Kubernetes experience.
    Education fully satisfies JD requirements.
    AWS certification preferred but not present.

Entirely template-based string generation over MatchResult.explanations[*]
.details — no LLM call, no network access, and no extra database or
embedding lookups. Deterministic given the same MatchResult.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.matching_service import MatchResult

Sentiment = Literal["positive", "negative", "neutral"]


@dataclass(frozen=True)
class ExplanationItem:
    text: str
    sentiment: Sentiment
    category: str  # "semantic" | "skills" | "experience" | "education" | "projects" | "certification"


# ── Thresholds ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExplanationThresholds:
    """Cutoffs and per-category caps that shape how many bullets get
    generated and how enthusiastically a match is phrased. Everything here
    is configurable — construct a custom instance and pass it to
    ExplainableMatchingService(thresholds=...)."""

    # Domain/industry background callouts (0-100 domain_relevance_score).
    strong_domain_relevance: float = 60.0
    weak_domain_relevance: float = 25.0

    # Experience: candidate_years / required_min_years.
    strong_experience_margin: float = 1.5

    # Education: score (0-100) at/above this counts as "fully satisfies".
    education_full_match: float = 99.9

    # Projects: per-requirement credit (0-1) at/above this counts as relevant.
    project_relevance_credit: float = 0.5

    # How many bullets to generate per positive skill tier before truncating.
    # Missing *required* skills are never truncated — that's the single most
    # actionable signal a recruiter reads this report for.
    max_exact_skill_highlights: int = 3
    max_synonym_skill_highlights: int = 2
    max_partial_skill_highlights: int = 2
    max_missing_preferred_highlights: int = 2
    max_preferred_matched_highlights: int = 2
    max_certification_highlights: int = 5
    max_project_highlights: int = 3


DEFAULT_THRESHOLDS = ExplanationThresholds()


# ── Service ──────────────────────────────────────────────────────────────────


class ExplainableMatchingService:
    """Stateless generator: construct once (optionally with custom
    thresholds) and call .explain(match_result) as many times as needed."""

    def __init__(self, thresholds: ExplanationThresholds | None = None) -> None:
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def explain(self, match_result: MatchResult) -> list[ExplanationItem]:
        items: list[ExplanationItem] = []
        items.extend(self._skill_items(match_result))
        items.extend(self._experience_items(match_result))
        items.extend(self._domain_items(match_result))
        items.extend(self._education_items(match_result))
        items.extend(self._project_items(match_result))
        items.extend(self._certification_items(match_result))
        return items

    def explain_as_text(self, match_result: MatchResult) -> list[str]:
        """Convenience wrapper for callers that just want plain bullet
        strings (e.g. rendering directly in a UI list)."""
        return [item.text for item in self.explain(match_result)]

    # ── Skills ────────────────────────────────────────────────────────────

    def _skill_items(self, match_result: MatchResult) -> list[ExplanationItem]:
        t = self.thresholds
        details = match_result.explanations["skills"].details
        required = details["required"]
        preferred = details["preferred"]
        items: list[ExplanationItem] = []

        for skill in required["exact_matches"][: t.max_exact_skill_highlights]:
            items.append(self._item(f"Excellent {skill} experience.", "positive", "skills"))
        for entry in required["synonym_matches"][: t.max_synonym_skill_highlights]:
            items.append(
                self._item(
                    f"Solid {entry['skill']} experience (via {entry['matched_to']}).",
                    "positive",
                    "skills",
                )
            )
        for entry in required["partial_matches"][: t.max_partial_skill_highlights]:
            items.append(
                self._item(
                    f"Some {entry['skill']} experience (partial match with {entry['matched_to']}).",
                    "neutral",
                    "skills",
                )
            )
        # Every missing *required* skill is actionable — never truncated.
        for skill in required["missing"]:
            items.append(self._item(f"Missing {skill} experience.", "negative", "skills"))

        preferred_matched = (
            preferred["exact_matches"]
            + [e["skill"] for e in preferred["synonym_matches"]]
            + [e["skill"] for e in preferred["partial_matches"]]
        )
        for skill in preferred_matched[: t.max_preferred_matched_highlights]:
            items.append(self._item(f"Bonus: {skill} experience (preferred).", "positive", "skills"))
        for skill in preferred["missing"][: t.max_missing_preferred_highlights]:
            items.append(self._item(f"{skill} preferred but not present.", "negative", "skills"))

        return items

    # ── Experience ────────────────────────────────────────────────────────

    def _experience_items(self, match_result: MatchResult) -> list[ExplanationItem]:
        t = self.thresholds
        details = match_result.explanations["experience"].details
        candidate_years = details["candidate_years"]
        required_min = details["required_min_years"]

        if required_min <= 0:
            return []

        margin = candidate_years / required_min
        if margin >= t.strong_experience_margin:
            text = f"Strong experience: {candidate_years:g} years (requirement: {required_min:g}+)."
            return [self._item(text, "positive", "experience")]
        if margin >= 1.0:
            text = f"Meets experience requirement: {candidate_years:g} years vs {required_min:g}+ required."
            return [self._item(text, "positive", "experience")]
        text = f"Below required experience: {candidate_years:g} years vs {required_min:g}+ required."
        return [self._item(text, "negative", "experience")]

    # ── Domain / semantic ─────────────────────────────────────────────────

    def _domain_items(self, match_result: MatchResult) -> list[ExplanationItem]:
        t = self.thresholds
        details = match_result.explanations["semantic"].details
        industry = details.get("industry")
        if not industry:
            return []

        relevance = details["domain_relevance_score"]
        if relevance >= t.strong_domain_relevance:
            return [self._item(f"Strong {industry} background.", "positive", "semantic")]
        if relevance <= t.weak_domain_relevance:
            return [
                self._item(
                    f"Limited {industry} background evident from the resume.", "negative", "semantic"
                )
            ]
        return []

    # ── Education ─────────────────────────────────────────────────────────

    def _education_items(self, match_result: MatchResult) -> list[ExplanationItem]:
        t = self.thresholds
        expl = match_result.explanations["education"]
        requirements = expl.details["requirements"]
        if not requirements:
            return []

        if expl.score >= t.education_full_match:
            return [self._item("Education fully satisfies JD.", "positive", "education")]
        if expl.score <= 0:
            return [self._item("Education does not meet JD requirements.", "negative", "education")]

        matched = sum(1 for r in requirements if r["credit"] >= 0.5)
        text = f"Education partially satisfies JD ({matched}/{len(requirements)} requirement(s) met)."
        return [self._item(text, "neutral", "education")]

    # ── Projects ──────────────────────────────────────────────────────────

    def _project_items(self, match_result: MatchResult) -> list[ExplanationItem]:
        t = self.thresholds
        requirements = match_result.explanations["projects"].details["requirements"]
        items: list[ExplanationItem] = []
        for r in requirements[: t.max_project_highlights]:
            if r["credit"] >= t.project_relevance_credit:
                text = f"Relevant project experience: {r['requirement']}."
                items.append(self._item(text, "positive", "projects"))
            else:
                text = f"No project experience matching '{r['requirement']}'."
                items.append(self._item(text, "negative", "projects"))
        return items

    # ── Certifications ────────────────────────────────────────────────────

    def _certification_items(self, match_result: MatchResult) -> list[ExplanationItem]:
        t = self.thresholds
        details = match_result.explanations["certification"].details
        items: list[ExplanationItem] = []
        for cert in details["matched"][: t.max_certification_highlights]:
            items.append(self._item(f"{cert} certification confirmed.", "positive", "certification"))
        for cert in details["missing"][: t.max_certification_highlights]:
            items.append(
                self._item(f"{cert} certification preferred but not present.", "negative", "certification")
            )
        return items

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _item(text: str, sentiment: Sentiment, category: str) -> ExplanationItem:
        return ExplanationItem(text=text, sentiment=sentiment, category=category)

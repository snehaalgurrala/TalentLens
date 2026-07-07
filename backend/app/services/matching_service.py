"""
MatchingService — deterministic, explainable scoring between a parsed resume
and a parsed job description.

No AI/LLM calls happen here: structured extraction (ai-services parsing
endpoints) and embeddings (EmbeddingService) are produced upstream and
passed in as plain data. This service only combines them into a weighted,
explainable match score, so it has no network or database dependency and
is fully deterministic given its inputs.

Semantic similarity is computed with the same cosine formula pgvector uses
for its `<=>` operator (cosine_distance = 1 - cosine_similarity) on the
embedding vectors stored in the `parsed_resumes.embedding` /
`job_descriptions.embedding` pgvector columns. Computing it in-process
(rather than issuing a SQL query) keeps this service DB-free and fully
unit-testable while remaining numerically identical to a pgvector query.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.job_description import JobDescription
    from app.models.parsed_resume import ParsedResume

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with",
    "at", "by", "from", "is", "are", "as", "years", "year",
}

# Groups of skill names that should be treated as equivalent even though
# they don't normalize to the same string (contrast with e.g. "Node.js" vs
# "nodejs", which normalization alone already unifies). Keys and values are
# matched case-insensitively; this is only the default — pass a custom
# MatchingWeights(skill_synonyms=...) to replace or extend it.
DEFAULT_SKILL_SYNONYMS: dict[str, list[str]] = {
    "js": ["javascript", "ecmascript"],
    "ts": ["typescript"],
    "py": ["python"],
    "golang": ["go"],
    "k8s": ["kubernetes"],
    "postgres": ["postgresql", "psql"],
    "mongo": ["mongodb"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud platform", "google cloud"],
    "azure": ["microsoft azure"],
    "ml": ["machine learning"],
    "ai": ["artificial intelligence"],
    "nlp": ["natural language processing"],
    "ci/cd": ["cicd", "continuous integration", "continuous deployment", "continuous delivery"],
    "react": ["reactjs", "react.js"],
    "vue": ["vuejs", "vue.js"],
    "node": ["nodejs", "node.js"],
}

# Degree "level" keywords ranked so a candidate's degree can be compared
# against a job description's requirement (e.g. "Master's required" is not
# satisfied by a Bachelor's). Matched as whole words against a lowercased,
# period-stripped string. Only the default — fully overridable via
# MatchingWeights(degree_rank_keywords=...).
DEFAULT_DEGREE_RANKS: dict[str, int] = {
    "phd": 4, "doctorate": 4, "doctoral": 4,
    "master": 3, "masters": 3, "msc": 3, "ms": 3, "ma": 3, "mba": 3, "meng": 3, "mtech": 3,
    "bachelor": 2, "bachelors": 2, "bsc": 2, "bs": 2, "ba": 2, "beng": 2, "btech": 2,
    "associate": 1, "diploma": 1,
}


# ── Weights ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MatchingWeights:
    """
    Every number that shapes a match score lives here. Construct a custom
    instance and pass it to MatchingService(weights=...) to change scoring
    behavior without touching any calculation code.
    """

    # Combine the six sub-scores into overall_score.
    semantic_weight: float = 0.30
    skills_weight: float = 0.25
    experience_weight: float = 0.15
    education_weight: float = 0.10
    projects_weight: float = 0.10
    certification_weight: float = 0.10

    # Combine embedding cosine similarity + domain relevance into semantic_score.
    cosine_weight: float = 0.8
    domain_weight: float = 0.2

    # Combine required vs preferred skill coverage into skills_score.
    required_skill_weight: float = 0.7
    preferred_skill_weight: float = 0.3

    # Per-skill credit by match tier (see MatchingService._classify_skill),
    # and the token-overlap ratio a skill pair must clear to count as a
    # "partial" match at all.
    exact_skill_credit: float = 1.0
    synonym_skill_credit: float = 0.9
    partial_skill_match_threshold: float = 0.6
    partial_skill_credit_scale: float = 0.75
    skill_synonyms: dict[str, list[str]] = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_SKILL_SYNONYMS.items()}
    )

    # Education: degree-level ranking, and how much a requirement's score
    # weighs degree-level match vs field-of-study overlap.
    degree_rank_keywords: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_DEGREE_RANKS)
    )
    education_degree_weight: float = 0.5
    education_field_weight: float = 0.5

    # Projects: how much a requirement's score weighs technology-list
    # overlap vs free-text description overlap.
    project_technology_weight: float = 0.6
    project_description_weight: float = 0.4

    # Minimum token-overlap ratio for a JD requirement (education field,
    # certification, or project description) to count as "matched" against
    # a resume entry.
    coverage_match_threshold: float = 0.3


DEFAULT_WEIGHTS = MatchingWeights()


# ── Result types ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScoreExplanation:
    """Human-readable breakdown backing a single score."""

    score: float
    weight: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "weight": self.weight,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass(frozen=True)
class MatchResult:
    overall_score: int
    semantic_score: int
    skills_score: int
    experience_score: int
    education_score: int
    projects_score: int
    certification_score: int
    explanations: dict[str, ScoreExplanation]

    def scores(self) -> dict[str, int]:
        """Exactly the shape TalentLens' matching contract expects."""
        return {
            "overall_score": self.overall_score,
            "semantic_score": self.semantic_score,
            "skills_score": self.skills_score,
            "experience_score": self.experience_score,
            "education_score": self.education_score,
            "projects_score": self.projects_score,
            "certification_score": self.certification_score,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.scores(),
            "explanations": {name: expl.to_dict() for name, expl in self.explanations.items()},
        }


# ── Text-matching primitives ────────────────────────────────────────────────


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


def _normalize_skill(text: str) -> str:
    """Lowercase with all non-alphanumeric characters stripped, so 'Node.js',
    'node-js' and 'NodeJS' all normalize to the same string."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _token_overlap_ratio(a: str, b: str) -> float:
    """Fraction of `a`'s significant tokens that also appear in `b`."""
    tokens_a = _tokenize(a)
    if not tokens_a:
        return 0.0
    tokens_b = _tokenize(b)
    if not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a)


def _best_match_ratio(target: str, candidates: list[str]) -> float:
    """Best token-overlap ratio between `target` and any string in `candidates`."""
    if not candidates:
        return 0.0
    return max((_token_overlap_ratio(target, c) for c in candidates), default=0.0)


def _clamp_pct(value: float) -> float:
    return max(0.0, min(100.0, value))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(
            f"Embedding dimension mismatch: resume={len(a)} vs job_description={len(b)}. "
            "Both embeddings must come from the same provider/model to be comparable."
        )
    # pgvector hands back embedding columns as numpy.float32 elements (via
    # numpy.ndarray or a list of boxed numpy scalars, depending on the
    # driver). Coercing to native float here — the single point where every
    # embedding enters scoring — keeps that numpy dtype from propagating
    # into ScoreExplanation.details, which Pydantic can't serialize.
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    norm_a = math.sqrt(sum(float(x) * float(x) for x in a))
    norm_b = math.sqrt(sum(float(y) * float(y) for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _build_synonym_index(skill_synonyms: dict[str, list[str]]) -> dict[str, str]:
    """Map each normalized skill spelling to a shared group id, so any two
    spellings in the same group can be recognized as synonyms."""
    index: dict[str, str] = {}
    for key, variants in skill_synonyms.items():
        group_id = _normalize_skill(key)
        index[group_id] = group_id
        for variant in variants:
            index[_normalize_skill(variant)] = group_id
    return index


def _synonym_group(normalized_skill: str, synonym_index: dict[str, str]) -> str:
    return synonym_index.get(normalized_skill, normalized_skill)


# ── MatchingService ──────────────────────────────────────────────────────────


class MatchingService:
    """
    Combines a parsed resume, a parsed job description, and their embeddings
    into an explainable, weighted match score.

    Only `.structured_json` is read off the resume/job_description arguments,
    so any object exposing that attribute works — a real ParsedResume /
    JobDescription row, or a lightweight stand-in in tests.
    """

    def __init__(self, weights: MatchingWeights | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS
        self._synonym_index = _build_synonym_index(self.weights.skill_synonyms)

    def calculate_match(
        self,
        resume: ParsedResume,
        job_description: JobDescription,
        resume_embedding: list[float],
        jd_embedding: list[float],
    ) -> MatchResult:
        resume_data = resume.structured_json
        jd_data = job_description.structured_json
        if not resume_data:
            raise ValueError("resume.structured_json is required for matching.")
        if not jd_data:
            raise ValueError("job_description.structured_json is required for matching.")
        # Embeddings may come back from pgvector as numpy arrays, whose
        # truthiness is ambiguous for more than one element — check
        # presence/length explicitly rather than with a bare `not`.
        if (
            resume_embedding is None
            or jd_embedding is None
            or len(resume_embedding) == 0
            or len(jd_embedding) == 0
        ):
            raise ValueError("Both resume_embedding and jd_embedding are required.")

        structured_resume = resume_data.get("structured_resume") or {}
        candidate_info = resume_data.get("candidate") or {}
        job = jd_data.get("job") or {}
        structured_jd = jd_data.get("structured_jd") or {}

        semantic_expl = self._semantic_score(
            resume_embedding, jd_embedding, structured_resume, candidate_info, job
        )
        skills_expl = self._skills_score(structured_resume, structured_jd)
        experience_expl = self._experience_score(candidate_info, job)
        education_expl = self._education_score(structured_resume, structured_jd)
        projects_expl = self._projects_score(structured_resume, structured_jd)
        certification_expl = self._certification_score(structured_resume, structured_jd)

        overall_expl = self._overall_score(
            semantic_expl, skills_expl, experience_expl, education_expl, projects_expl, certification_expl
        )

        return MatchResult(
            overall_score=round(overall_expl.score),
            semantic_score=round(semantic_expl.score),
            skills_score=round(skills_expl.score),
            experience_score=round(experience_expl.score),
            education_score=round(education_expl.score),
            projects_score=round(projects_expl.score),
            certification_score=round(certification_expl.score),
            explanations={
                "overall": overall_expl,
                "semantic": semantic_expl,
                "skills": skills_expl,
                "experience": experience_expl,
                "education": education_expl,
                "projects": projects_expl,
                "certification": certification_expl,
            },
        )

    # ── Sub-scores ────────────────────────────────────────────────────────

    def _overall_score(
        self, semantic, skills, experience, education, projects, certification
    ) -> ScoreExplanation:
        w = self.weights
        raw = (
            semantic.score * w.semantic_weight
            + skills.score * w.skills_weight
            + experience.score * w.experience_weight
            + education.score * w.education_weight
            + projects.score * w.projects_weight
            + certification.score * w.certification_weight
        )
        return ScoreExplanation(
            score=_clamp_pct(raw),
            weight=1.0,
            summary="Weighted combination of semantic, skills, experience, education, projects, and certification scores.",
            details={
                "semantic_weight": w.semantic_weight,
                "skills_weight": w.skills_weight,
                "experience_weight": w.experience_weight,
                "education_weight": w.education_weight,
                "projects_weight": w.projects_weight,
                "certification_weight": w.certification_weight,
            },
        )

    def _semantic_score(
        self, resume_embedding, jd_embedding, structured_resume, candidate_info, job
    ) -> ScoreExplanation:
        similarity = cosine_similarity(resume_embedding, jd_embedding)
        cosine_pct = _clamp_pct(((similarity + 1) / 2) * 100)
        domain_pct = self._domain_relevance(structured_resume, candidate_info, job)

        w = self.weights
        score = cosine_pct * w.cosine_weight + domain_pct * w.domain_weight
        return ScoreExplanation(
            score=_clamp_pct(score),
            weight=w.semantic_weight,
            summary=(
                f"Embedding similarity {cosine_pct:.0f}% blended with "
                f"domain relevance {domain_pct:.0f}%."
            ),
            details={
                "cosine_similarity": round(similarity, 4),
                "cosine_score": round(cosine_pct, 1),
                "domain_relevance_score": round(domain_pct, 1),
                "cosine_weight": w.cosine_weight,
                "domain_weight": w.domain_weight,
                "industry": (job.get("industry") or "").strip() or None,
            },
        )

    def _domain_relevance(self, structured_resume, candidate_info, job) -> float:
        industry = (job.get("industry") or "").strip()
        if not industry:
            return 100.0

        blob_parts = [
            candidate_info.get("current_role") or "",
            candidate_info.get("current_company") or "",
            structured_resume.get("summary") or "",
            " ".join(structured_resume.get("skills") or []),
        ]
        for exp in structured_resume.get("experience") or []:
            blob_parts.append(exp.get("role") or "")
            blob_parts.append(exp.get("description") or "")

        ratio = _token_overlap_ratio(industry, " ".join(blob_parts))
        return _clamp_pct(ratio * 100)

    # ── Skills ────────────────────────────────────────────────────────────

    def _classify_skill(
        self, jd_skill: str, resume_skills: list[str]
    ) -> tuple[str, float, str | None]:
        """Classify a single JD skill against the candidate's skill list.

        Returns (tier, credit, matched_resume_skill) where tier is one of
        "exact", "synonym", "partial", "none" and credit is the [0, 1]
        contribution that skill makes toward coverage.
        """
        w = self.weights
        norm_jd = _normalize_skill(jd_skill)

        for resume_skill in resume_skills:
            if _normalize_skill(resume_skill) == norm_jd:
                return "exact", w.exact_skill_credit, resume_skill

        jd_group = _synonym_group(norm_jd, self._synonym_index)
        for resume_skill in resume_skills:
            if _synonym_group(_normalize_skill(resume_skill), self._synonym_index) == jd_group:
                return "synonym", w.synonym_skill_credit, resume_skill

        best_ratio = 0.0
        best_skill: str | None = None
        for resume_skill in resume_skills:
            ratio = _token_overlap_ratio(jd_skill, resume_skill)
            if ratio > best_ratio:
                best_ratio, best_skill = ratio, resume_skill
        if best_ratio >= w.partial_skill_match_threshold:
            return "partial", w.partial_skill_credit_scale * best_ratio, best_skill

        return "none", 0.0, None

    def _score_skill_list(
        self, jd_skills: list[str], resume_skills: list[str]
    ) -> tuple[float, dict[str, Any]]:
        """Score one JD skill list (required or preferred) against the
        candidate's skills. Returns (coverage_ratio, details)."""
        exact, synonym, partial, missing = [], [], [], []
        credit_sum = 0.0
        for jd_skill in jd_skills:
            tier, credit, matched = self._classify_skill(jd_skill, resume_skills)
            credit_sum += credit
            if tier == "exact":
                exact.append(jd_skill)
            elif tier == "synonym":
                synonym.append({"skill": jd_skill, "matched_to": matched})
            elif tier == "partial":
                partial.append({"skill": jd_skill, "matched_to": matched})
            else:
                missing.append(jd_skill)

        coverage = (credit_sum / len(jd_skills)) if jd_skills else 1.0
        return coverage, {
            "skills": jd_skills,
            "exact_matches": exact,
            "synonym_matches": synonym,
            "partial_matches": partial,
            "missing": missing,
        }

    def _skills_score(self, structured_resume, structured_jd) -> ScoreExplanation:
        resume_skills = [s.strip() for s in (structured_resume.get("skills") or []) if s.strip()]
        required = [s.strip() for s in (structured_jd.get("required_skills") or []) if s.strip()]
        preferred = [s.strip() for s in (structured_jd.get("preferred_skills") or []) if s.strip()]

        required_coverage, required_details = self._score_skill_list(required, resume_skills)
        preferred_coverage, preferred_details = self._score_skill_list(preferred, resume_skills)

        w = self.weights
        score = (
            required_coverage * w.required_skill_weight
            + preferred_coverage * w.preferred_skill_weight
        ) * 100

        matched_required = (
            len(required_details["exact_matches"])
            + len(required_details["synonym_matches"])
            + len(required_details["partial_matches"])
        )
        matched_preferred = (
            len(preferred_details["exact_matches"])
            + len(preferred_details["synonym_matches"])
            + len(preferred_details["partial_matches"])
        )

        return ScoreExplanation(
            score=_clamp_pct(score),
            weight=w.skills_weight,
            summary=(
                f"{matched_required}/{len(required)} required skills matched, "
                f"{matched_preferred}/{len(preferred)} preferred skills matched."
            ),
            details={
                "required": required_details,
                "preferred": preferred_details,
                "required_skill_weight": w.required_skill_weight,
                "preferred_skill_weight": w.preferred_skill_weight,
            },
        )

    def _experience_score(self, candidate_info, job) -> ScoreExplanation:
        candidate_years = float(candidate_info.get("years_of_experience") or 0)
        exp_min = float(job.get("experience_min") or 0)
        exp_max = float(job.get("experience_max") or 0)

        if exp_min <= 0:
            score = 100.0
            summary = "No minimum experience requirement stated."
        elif candidate_years >= exp_min:
            score = 100.0
            summary = f"Candidate has {candidate_years:g} years, meeting the {exp_min:g}+ year requirement."
        else:
            score = _clamp_pct((candidate_years / exp_min) * 100)
            summary = f"Candidate has {candidate_years:g} years, below the {exp_min:g} year requirement."

        return ScoreExplanation(
            score=score,
            weight=self.weights.experience_weight,
            summary=summary,
            details={
                "candidate_years": candidate_years,
                "required_min_years": exp_min,
                "required_max_years": exp_max,
            },
        )

    # ── Education ─────────────────────────────────────────────────────────

    def _extract_degree_rank(self, text: str) -> int | None:
        normalized = re.sub(r"\.", "", (text or "").lower())
        best_rank: int | None = None
        for keyword, rank in self.weights.degree_rank_keywords.items():
            if re.search(rf"\b{re.escape(keyword)}\b", normalized):
                if best_rank is None or rank > best_rank:
                    best_rank = rank
        return best_rank

    def _score_education_requirement(self, requirement: str, candidates: list[dict]) -> dict:
        w = self.weights
        req_rank = self._extract_degree_rank(requirement)

        best_credit = 0.0
        best_candidate: dict | None = None
        for candidate in candidates:
            cand_degree = candidate.get("degree") or ""
            cand_rank = self._extract_degree_rank(cand_degree)

            if req_rank is None:
                degree_credit = 1.0
            elif cand_rank is None:
                degree_credit = 0.0
            elif cand_rank >= req_rank:
                degree_credit = 1.0
            else:
                degree_credit = cand_rank / req_rank

            field_blob = " ".join(
                filter(None, [candidate.get("field"), candidate.get("institution")])
            )
            field_ratio = _token_overlap_ratio(requirement, field_blob)
            field_credit = 1.0 if field_ratio >= w.coverage_match_threshold else 0.0

            credit = degree_credit * w.education_degree_weight + field_credit * w.education_field_weight
            if credit > best_credit:
                best_credit = credit
                best_candidate = {
                    "institution": candidate.get("institution"),
                    "degree": cand_degree,
                    "field": candidate.get("field"),
                    "degree_credit": degree_credit,
                    "field_credit": field_credit,
                }

        return {
            "requirement": requirement,
            "required_degree_rank": req_rank,
            "credit": best_credit,
            "best_match": best_candidate,
        }

    def _education_score(self, structured_resume, structured_jd) -> ScoreExplanation:
        required = [e.strip() for e in (structured_jd.get("education") or []) if e.strip()]
        w = self.weights

        if not required:
            return ScoreExplanation(
                score=100.0,
                weight=w.education_weight,
                summary="No education requirement(s) specified in the job description.",
                details={"requirements": []},
            )

        candidates = structured_resume.get("education") or []
        results = [self._score_education_requirement(req, candidates) for req in required]
        avg_credit = sum(r["credit"] for r in results) / len(results)
        matched = sum(1 for r in results if r["credit"] >= 0.5)

        return ScoreExplanation(
            score=_clamp_pct(avg_credit * 100),
            weight=w.education_weight,
            summary=f"{matched}/{len(required)} education requirement(s) matched.",
            details={
                "requirements": results,
                "education_degree_weight": w.education_degree_weight,
                "education_field_weight": w.education_field_weight,
            },
        )

    def _certification_score(self, structured_resume, structured_jd) -> ScoreExplanation:
        required = [c for c in (structured_jd.get("certifications") or []) if c.strip()]
        candidate_entries = [
            " ".join(filter(None, [c.get("name"), c.get("issuer")]))
            for c in (structured_resume.get("certifications") or [])
        ]
        return self._coverage_score(
            required,
            candidate_entries,
            weight=self.weights.certification_weight,
            label="certification(s)",
        )

    # ── Projects ──────────────────────────────────────────────────────────

    def _technology_mentioned(self, technology: str, requirement_tokens: set[str]) -> bool:
        tech_tokens = _tokenize(technology)
        return bool(tech_tokens) and tech_tokens.issubset(requirement_tokens)

    def _score_project_requirement(self, requirement: str, candidates: list[dict]) -> dict:
        w = self.weights
        requirement_tokens = _tokenize(requirement)

        best_credit = 0.0
        best_candidate: dict | None = None
        for candidate in candidates:
            technologies = [t.strip() for t in (candidate.get("technologies") or []) if t.strip()]
            if technologies:
                mentioned = [t for t in technologies if self._technology_mentioned(t, requirement_tokens)]
                tech_credit = len(mentioned) / len(technologies)
            else:
                mentioned = []
                tech_credit = 0.0

            desc_blob = " ".join(filter(None, [candidate.get("name"), candidate.get("description")]))
            desc_ratio = _token_overlap_ratio(requirement, desc_blob)
            desc_credit = 1.0 if desc_ratio >= w.coverage_match_threshold else 0.0

            credit = tech_credit * w.project_technology_weight + desc_credit * w.project_description_weight
            if credit > best_credit:
                best_credit = credit
                best_candidate = {
                    "name": candidate.get("name"),
                    "technologies": technologies,
                    "technologies_matched": mentioned,
                    "tech_credit": tech_credit,
                    "desc_credit": desc_credit,
                }

        return {"requirement": requirement, "credit": best_credit, "best_match": best_candidate}

    def _projects_score(self, structured_resume, structured_jd) -> ScoreExplanation:
        required = [p.strip() for p in (structured_jd.get("projects") or []) if p.strip()]
        w = self.weights

        if not required:
            return ScoreExplanation(
                score=100.0,
                weight=w.projects_weight,
                summary="No relevant project(s) specified in the job description.",
                details={"requirements": []},
            )

        candidates = structured_resume.get("projects") or []
        results = [self._score_project_requirement(req, candidates) for req in required]
        avg_credit = sum(r["credit"] for r in results) / len(results)
        matched = sum(1 for r in results if r["credit"] >= 0.5)

        return ScoreExplanation(
            score=_clamp_pct(avg_credit * 100),
            weight=w.projects_weight,
            summary=f"{matched}/{len(required)} relevant project(s) matched.",
            details={
                "requirements": results,
                "project_technology_weight": w.project_technology_weight,
                "project_description_weight": w.project_description_weight,
            },
        )

    # ── Generic coverage (certifications) ───────────────────────────────────

    def _coverage_score(
        self,
        required: list[str],
        candidate_entries: list[str],
        *,
        weight: float,
        label: str,
    ) -> ScoreExplanation:
        if not required:
            return ScoreExplanation(
                score=100.0,
                weight=weight,
                summary=f"No {label} specified in the job description.",
                details={"required": [], "matched": [], "missing": []},
            )

        threshold = self.weights.coverage_match_threshold
        matched = [
            item for item in required if _best_match_ratio(item, candidate_entries) >= threshold
        ]

        return ScoreExplanation(
            score=_clamp_pct((len(matched) / len(required)) * 100),
            weight=weight,
            summary=f"{len(matched)}/{len(required)} {label} matched.",
            details={
                "required": required,
                "matched": matched,
                "missing": [r for r in required if r not in matched],
            },
        )

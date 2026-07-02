"""
CandidateRankingService — ranks every candidate in a campaign against the
campaign's job description.

Sub-scores come from MatchingService; they're combined into a final score
using the campaign's *effective* scoring rule (ScoringRuleService.get_effective:
campaign override -> organization default -> system default).

Rankings are computed fresh from current database state on every call —
there is no persisted/cached ranking to invalidate. That means a ranking
automatically reflects the latest resume, job description, or scoring rule
as soon as any of them changes; there's nothing to explicitly "update".
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.embedding import EmbeddingStatus
from app.models.job_description import ParsingStatus
from app.models.resume_file import UploadStatus
from app.services.matching_service import MatchingService, MatchResult
from app.services.scoring_rule import compute_score_breakdown

if TYPE_CHECKING:
    from app.models.candidate import Candidate
    from app.models.job_description import JobDescription
    from app.models.resume_file import ResumeFile
    from app.models.user import User
    from app.repositories.campaign import CampaignRepository
    from app.repositories.candidate import CandidateRepository
    from app.repositories.job_description import JobDescriptionRepository
    from app.repositories.parsed_resume import ParsedResumeRepository
    from app.repositories.resume_file import ResumeFileRepository
    from app.schemas.scoring_rule import EffectiveScoringRuleResponse
    from app.services.scoring_rule import ScoreBreakdown, ScoringRuleService


# ── Thresholds ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RankingThresholds:
    """Score cutoffs (0-100) that turn a raw overall_score into a
    human-readable recommendation, and that decide which sub-scores get
    called out as strengths vs. weaknesses."""

    strong_match: float = 85.0
    good_match: float = 70.0
    possible_match: float = 50.0
    # below possible_match -> "Not a Match"
    strength_score: float = 75.0
    weakness_score: float = 50.0


DEFAULT_THRESHOLDS = RankingThresholds()

# (MatchResult.explanations key, human label) — iterated in a fixed, stable
# order so strengths/weaknesses lists read the same way every time.
_SUB_SCORE_LABELS: tuple[tuple[str, str], ...] = (
    ("semantic", "Semantic fit"),
    ("skills", "Skills"),
    ("experience", "Experience"),
    ("education", "Education"),
    ("projects", "Projects"),
    ("certification", "Certifications"),
)

_SOURCE_LABELS = {
    "campaign_override": "a campaign-specific scoring rule",
    "organization_default": "the organization's default scoring rule",
    "system_default": "the system default scoring weights",
}


# ── Result type ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CandidateRankingEntry:
    rank: int
    candidate_id: uuid.UUID
    candidate_name: str
    resume_file_id: uuid.UUID
    overall_score: float
    match_result: MatchResult
    recommendation: str
    strengths: list[str]
    weaknesses: list[str]
    match_explanation: str
    scoring_rule_source: str


# ── Service ──────────────────────────────────────────────────────────────────


class CandidateRankingService:
    def __init__(
        self,
        campaign_repo: CampaignRepository,
        resume_file_repo: ResumeFileRepository,
        parsed_resume_repo: ParsedResumeRepository,
        candidate_repo: CandidateRepository,
        job_description_repo: JobDescriptionRepository,
        scoring_rule_service: ScoringRuleService,
        matching_service: MatchingService | None = None,
        thresholds: RankingThresholds | None = None,
    ) -> None:
        self.campaign_repo = campaign_repo
        self.resume_file_repo = resume_file_repo
        self.parsed_resume_repo = parsed_resume_repo
        self.candidate_repo = candidate_repo
        self.job_description_repo = job_description_repo
        self.scoring_rule_service = scoring_rule_service
        self.matching_service = matching_service or MatchingService()
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    # ── Internal guards ──────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to rank candidates.",
            )
        return user.org_id

    async def _require_campaign(self, campaign_id: uuid.UUID, org_id: uuid.UUID):
        campaign = await self.campaign_repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return campaign

    async def _get_ready_job_description(self, campaign_id: uuid.UUID) -> JobDescription:
        """The most recently created job description for this campaign that
        has finished parsing and has a usable embedding. A campaign can have
        several job descriptions (revisions); we rank against the latest one
        that's actually ready."""
        job_descriptions = await self.job_description_repo.list_by_campaign(campaign_id)
        for jd in job_descriptions:
            if (
                jd.parsing_status == ParsingStatus.COMPLETED
                and jd.embedding_status == EmbeddingStatus.READY
                and jd.embedding is not None
            ):
                return jd
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "This campaign has no job description that has finished parsing "
                "and embedding yet, so candidates cannot be ranked."
            ),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def rank_campaign(
        self, campaign_id: uuid.UUID, user: User
    ) -> list[CandidateRankingEntry]:
        org_id = self._require_org(user)
        await self._require_campaign(campaign_id, org_id)

        job_description = await self._get_ready_job_description(campaign_id)
        effective_rule = await self.scoring_rule_service.get_effective(campaign_id, user)

        resume_files = await self.resume_file_repo.list_by_campaign(campaign_id)
        ready_files = [
            rf
            for rf in resume_files
            if rf.upload_status == UploadStatus.PARSED and rf.candidate_id is not None
        ]
        if not ready_files:
            return []

        parsed_resumes = await self.parsed_resume_repo.list_by_resume_file_ids(
            [rf.id for rf in ready_files]
        )
        parsed_by_resume_file = {
            pr.resume_file_id: pr
            for pr in parsed_resumes
            if pr.embedding_status == EmbeddingStatus.READY and pr.embedding is not None
        }

        candidate_ids = list(
            {rf.candidate_id for rf in ready_files if rf.id in parsed_by_resume_file}
        )
        candidates_by_id = {c.id: c for c in await self.candidate_repo.list_by_ids(candidate_ids)}

        unranked: list[CandidateRankingEntry] = []
        for resume_file in ready_files:
            parsed_resume = parsed_by_resume_file.get(resume_file.id)
            if parsed_resume is None:
                continue
            candidate = candidates_by_id.get(resume_file.candidate_id)
            if candidate is None:
                continue

            match_result = self.matching_service.calculate_match(
                parsed_resume,
                job_description,
                parsed_resume.embedding,
                job_description.embedding,
            )
            breakdown = compute_score_breakdown(
                effective_rule,
                semantic_score=match_result.semantic_score,
                skills_score=match_result.skills_score,
                experience_score=match_result.experience_score,
                education_score=match_result.education_score,
                project_score=match_result.projects_score,
                certification_score=match_result.certification_score,
                candidate_company=candidate.current_company,
            )
            unranked.append(
                self._build_entry(candidate, resume_file, match_result, breakdown, effective_rule)
            )

        unranked.sort(key=lambda entry: (-entry.overall_score, entry.candidate_name.lower()))
        return [
            dataclasses.replace(entry, rank=rank)
            for rank, entry in enumerate(unranked, start=1)
        ]

    # ── Entry construction ──────────────────────────────────────────────────

    def _build_entry(
        self,
        candidate: Candidate,
        resume_file: ResumeFile,
        match_result: MatchResult,
        breakdown: ScoreBreakdown,
        rule: EffectiveScoringRuleResponse,
    ) -> CandidateRankingEntry:
        candidate_name = f"{candidate.first_name} {candidate.last_name}".strip()
        recommendation = self._recommendation(breakdown.final_score)
        strengths, weaknesses = self._strengths_and_weaknesses(match_result)
        if breakdown.preferred_company_matched:
            strengths.append(
                f"Preferred employer: {candidate.current_company} "
                f"(+{breakdown.bonus_points:.0f} point bonus)."
            )
        explanation = self._match_explanation(candidate_name, breakdown, recommendation, match_result, rule.source)

        return CandidateRankingEntry(
            rank=0,  # assigned by rank_campaign once the full order is known
            candidate_id=candidate.id,
            candidate_name=candidate_name,
            resume_file_id=resume_file.id,
            overall_score=round(breakdown.final_score, 1),
            match_result=match_result,
            recommendation=recommendation,
            strengths=strengths,
            weaknesses=weaknesses,
            match_explanation=explanation,
            scoring_rule_source=rule.source,
        )

    def _recommendation(self, score: float) -> str:
        t = self.thresholds
        if score >= t.strong_match:
            return "Strong Match"
        if score >= t.good_match:
            return "Good Match"
        if score >= t.possible_match:
            return "Possible Match"
        return "Not a Match"

    def _strengths_and_weaknesses(self, match_result: MatchResult) -> tuple[list[str], list[str]]:
        t = self.thresholds
        strengths: list[str] = []
        weaknesses: list[str] = []
        for key, label in _SUB_SCORE_LABELS:
            expl = match_result.explanations[key]
            if expl.score >= t.strength_score:
                strengths.append(f"{label}: {expl.summary}")
            elif expl.score <= t.weakness_score:
                weaknesses.append(f"{label}: {expl.summary}")
        return strengths, weaknesses

    def _match_explanation(
        self,
        candidate_name: str,
        breakdown: ScoreBreakdown,
        recommendation: str,
        match_result: MatchResult,
        source: str,
    ) -> str:
        parts = [
            f"{candidate_name} scored {breakdown.final_score:.0f}/100 overall ({recommendation}).",
            match_result.explanations["overall"].summary,
        ]
        if breakdown.preferred_company_matched:
            parts.append(
                f"A +{breakdown.bonus_points:.0f} point preferred-employer bonus was applied."
            )
        parts.append(f"Scored using {_SOURCE_LABELS[source]}.")
        return " ".join(parts)

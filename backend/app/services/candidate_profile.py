"""
CandidateProfileService — the single-candidate workspace behind
/candidates/{id}/profile and /candidates/{id}/match-analysis.

Resolves the id ambiguity baked into the candidate list (see
CandidateManagementService._to_list_item): the id a recruiter navigates with
may be a real Candidate.id, or — if parsing hasn't produced a Candidate row
yet — the underlying ResumeFile.id used as a stand-in. Both resolve to the
same ResumeFile that every mutation endpoint already keys on.

Match/ranking data is never recomputed or duplicated here: rank_campaign()
is reused as-is and this service just picks out the one entry that matches
the resolved resume_file_id, so a candidate's profile score is always
identical to their row in the campaign ranking list.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.models.candidate_activity import ActivityEventType
from app.schemas.candidate_profile import (
    CandidateMatchAnalysisExplanationItem,
    CandidateMatchAnalysisResponse,
    CandidateProfileCampaign,
    CandidateProfileResponse,
    StructuredCertificationItem,
    StructuredEducationItem,
    StructuredExperienceItem,
    StructuredProjectItem,
    StructuredResumeContent,
)
from app.schemas.candidate_ranking import RankingSubScores
from app.schemas.user import UserSummaryResponse
from app.services.candidate_lookup import resolve_resume_file as _resolve_resume_file
from app.services.explainable_matching import ExplainableMatchingService

if TYPE_CHECKING:
    from app.models.resume_file import ResumeFile
    from app.models.user import User
    from app.repositories.candidate import CandidateRepository
    from app.repositories.candidate_activity import CandidateActivityRepository
    from app.repositories.campaign import CampaignRepository
    from app.repositories.parsed_resume import ParsedResumeRepository
    from app.repositories.resume_file import ResumeFileRepository
    from app.repositories.user import UserRepository
    from app.services.candidate_ranking import CandidateRankingEntry, CandidateRankingService


class CandidateProfileService:
    def __init__(
        self,
        resume_file_repo: ResumeFileRepository,
        candidate_repo: CandidateRepository,
        parsed_resume_repo: ParsedResumeRepository,
        campaign_repo: CampaignRepository,
        user_repo: UserRepository,
        activity_repo: CandidateActivityRepository,
        ranking_service: CandidateRankingService,
        explainable_service: ExplainableMatchingService | None = None,
    ) -> None:
        self.resume_file_repo = resume_file_repo
        self.candidate_repo = candidate_repo
        self.parsed_resume_repo = parsed_resume_repo
        self.campaign_repo = campaign_repo
        self.user_repo = user_repo
        self.activity_repo = activity_repo
        self.ranking_service = ranking_service
        self.explainable_service = explainable_service or ExplainableMatchingService()

    # ── Internal guards ──────────────────────────────────────────────────────

    def _require_org(self, user: User) -> uuid.UUID:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view candidates.",
            )
        return user.org_id

    async def _require_campaign(self, campaign_id: uuid.UUID, org_id: uuid.UUID):
        campaign = await self.campaign_repo.get_by_id(campaign_id, org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found.",
            )
        return campaign

    async def resolve_resume_file(self, id_: uuid.UUID, user: User) -> ResumeFile:
        """Accepts either a Candidate.id or a ResumeFile.id (the two ids the
        candidate list can hand back) and returns the underlying ResumeFile."""
        org_id = self._require_org(user)
        return await _resolve_resume_file(
            id_, org_id, self.resume_file_repo, self.candidate_repo, self.campaign_repo
        )

    async def _find_ranking_entry(
        self, rf: ResumeFile, user: User
    ) -> tuple[bool, CandidateRankingEntry | None]:
        """Returns (ranking_available, entry). ranking_available is False only
        when the campaign has no JD ready to rank against at all; entry is
        None whenever this specific candidate isn't in the ranked set yet
        (e.g. still parsing/embedding)."""
        try:
            entries = await self.ranking_service.rank_campaign(rf.campaign_id, user)
        except HTTPException:
            return False, None
        entry = next((e for e in entries if e.resume_file_id == rf.id), None)
        return True, entry

    def _structured_resume(self, parsed) -> tuple[StructuredResumeContent, float | None]:
        if parsed is None or not parsed.structured_json:
            return StructuredResumeContent(), None
        data = parsed.structured_json
        structured = data.get("structured_resume") or {}
        content = StructuredResumeContent(
            skills=[s for s in (structured.get("skills") or []) if s],
            experience=[StructuredExperienceItem(**e) for e in (structured.get("experience") or [])],
            education=[StructuredEducationItem(**e) for e in (structured.get("education") or [])],
            projects=[StructuredProjectItem(**p) for p in (structured.get("projects") or [])],
            certifications=[
                StructuredCertificationItem(**c) for c in (structured.get("certifications") or [])
            ],
            summary=structured.get("summary") or None,
        )
        return content, data.get("confidence")

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_profile(self, id_: uuid.UUID, user: User) -> CandidateProfileResponse:
        rf = await self.resolve_resume_file(id_, user)
        org_id = self._require_org(user)
        campaign = await self._require_campaign(rf.campaign_id, org_id)

        candidates = (
            await self.candidate_repo.list_by_ids([rf.candidate_id])
            if rf.candidate_id is not None
            else []
        )
        candidate = candidates[0] if candidates else None

        parsed = await self.parsed_resume_repo.find_by_resume_file(rf.id)
        structured_resume, parse_confidence = self._structured_resume(parsed)

        ranking_available, entry = await self._find_ranking_entry(rf, user)

        await self.activity_repo.create(rf.id, user.id, ActivityEventType.VIEWED)

        candidate_name = (
            f"{candidate.first_name} {candidate.last_name}".strip()
            if candidate is not None
            else rf.original_filename
        )

        assigned_recruiter_response = None
        if rf.assigned_recruiter_id is not None:
            recruiter = await self.user_repo.get_by_id(rf.assigned_recruiter_id)
            if recruiter is not None:
                assigned_recruiter_response = UserSummaryResponse.model_validate(recruiter)

        return CandidateProfileResponse(
            resume_file_id=rf.id,
            candidate_id=candidate.id if candidate is not None else rf.id,
            candidate_name=candidate_name,
            email=candidate.email if candidate else None,
            phone=candidate.phone if candidate else None,
            location=candidate.location if candidate else None,
            linkedin_url=candidate.linkedin_url if candidate else None,
            github_url=candidate.github_url if candidate else None,
            current_company=candidate.current_company if candidate else None,
            current_role=candidate.current_role if candidate else None,
            years_of_experience=candidate.years_of_experience if candidate else None,
            structured_resume=structured_resume,
            parse_confidence=parse_confidence,
            campaign=CandidateProfileCampaign(id=campaign.id, title=campaign.title),
            upload_status=rf.upload_status,
            review_status=rf.review_status,
            pipeline_stage=rf.pipeline_stage,
            assigned_recruiter=assigned_recruiter_response,
            uploaded_at=rf.uploaded_at,
            overall_score=entry.overall_score if entry else None,
            sub_scores=(
                RankingSubScores(
                    semantic_score=entry.match_result.semantic_score,
                    skills_score=entry.match_result.skills_score,
                    experience_score=entry.match_result.experience_score,
                    education_score=entry.match_result.education_score,
                    projects_score=entry.match_result.projects_score,
                    certification_score=entry.match_result.certification_score,
                )
                if entry
                else None
            ),
            recommendation=entry.recommendation if entry else None,
            ranking_available=ranking_available,
        )

    async def get_match_analysis(self, id_: uuid.UUID, user: User) -> CandidateMatchAnalysisResponse:
        rf = await self.resolve_resume_file(id_, user)
        _, entry = await self._find_ranking_entry(rf, user)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "This candidate has not been ranked yet — the campaign's job "
                    "description may still be parsing, or this resume hasn't finished "
                    "parsing/embedding."
                ),
            )

        match_result = entry.match_result
        explanations = match_result.explanations
        items = self.explainable_service.explain(match_result)

        return CandidateMatchAnalysisResponse(
            overall_score=entry.overall_score,
            recommendation=entry.recommendation,  # type: ignore[arg-type]
            sub_scores=RankingSubScores(
                semantic_score=match_result.semantic_score,
                skills_score=match_result.skills_score,
                experience_score=match_result.experience_score,
                education_score=match_result.education_score,
                projects_score=match_result.projects_score,
                certification_score=match_result.certification_score,
            ),
            bonus_points=entry.bonus_points,
            preferred_company_matched=entry.preferred_company_matched,
            scoring_rule_source=entry.scoring_rule_source,  # type: ignore[arg-type]
            match_explanation=entry.match_explanation,
            strengths=entry.strengths,
            weaknesses=entry.weaknesses,
            semantic_details=explanations["semantic"].details,
            skills_details=explanations["skills"].details,
            experience_details=explanations["experience"].details,
            education_details=explanations["education"].details,
            projects_details=explanations["projects"].details,
            certification_details=explanations["certification"].details,
            explanation_items=[
                CandidateMatchAnalysisExplanationItem(
                    text=i.text, sentiment=i.sentiment, category=i.category
                )
                for i in items
            ],
        )

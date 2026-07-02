import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.job_description import JobDescriptionRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.schemas.candidate_ranking import CandidateRankingResponse, RankingSubScores
from app.services.candidate_ranking import CandidateRankingService
from app.services.scoring_rule import ScoringRuleService

router = APIRouter()

# ── Dependency factory (overridable in tests) ─────────────────────────────────


def get_candidate_ranking_service(db: DBSession) -> CandidateRankingService:
    return CandidateRankingService(
        campaign_repo=CampaignRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        candidate_repo=CandidateRepository(db),
        job_description_repo=JobDescriptionRepository(db),
        scoring_rule_service=ScoringRuleService(ScoringRuleRepository(db), CampaignRepository(db)),
    )


CandidateRankingServiceDep = Annotated[CandidateRankingService, Depends(get_candidate_ranking_service)]

# Rankings expose internal scoring detail; candidates have no legitimate use for it.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def _to_response(entry) -> CandidateRankingResponse:
    return CandidateRankingResponse(
        rank=entry.rank,
        candidate_id=entry.candidate_id,
        candidate_name=entry.candidate_name,
        resume_file_id=entry.resume_file_id,
        overall_score=entry.overall_score,
        sub_scores=RankingSubScores(
            semantic_score=entry.match_result.semantic_score,
            skills_score=entry.match_result.skills_score,
            experience_score=entry.match_result.experience_score,
            education_score=entry.match_result.education_score,
            projects_score=entry.match_result.projects_score,
            certification_score=entry.match_result.certification_score,
        ),
        recommendation=entry.recommendation,
        strengths=entry.strengths,
        weaknesses=entry.weaknesses,
        match_explanation=entry.match_explanation,
        scoring_rule_source=entry.scoring_rule_source,
        current_company=entry.current_company,
        years_of_experience=entry.years_of_experience,
        review_status=entry.review_status,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/campaigns/{campaign_id}/rankings",
    response_model=list[CandidateRankingResponse],
    summary="Rank every candidate in a campaign against its job description",
    responses={
        200: {
            "description": (
                "Ordered ranking list, highest overall_score first. Computed fresh from "
                "the current resume, job description, and scoring rule — always up to date."
            )
        },
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
        422: {
            "description": (
                "User has no organization, or the campaign has no job description that "
                "has finished parsing and embedding yet."
            )
        },
    },
)
async def rank_campaign_candidates(
    campaign_id: uuid.UUID,
    service: CandidateRankingServiceDep,
    current_user: RecruiterUser,
) -> list[CandidateRankingResponse]:
    entries = await service.rank_campaign(campaign_id, current_user)
    return [_to_response(entry) for entry in entries]

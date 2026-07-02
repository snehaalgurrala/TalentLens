from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.job_description import JobDescriptionRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.schemas.dashboard import (
    ActivityItemResponse,
    DashboardSummaryResponse,
    ProcessingStatusResponse,
    RecentCampaignResponse,
    TopCandidateResponse,
)
from app.services.candidate_ranking import CandidateRankingService
from app.services.dashboard import DashboardService
from app.services.scoring_rule import ScoringRuleService

router = APIRouter()

# ── Dependency factory (overridable in tests) ─────────────────────────────────


def get_dashboard_service(db: DBSession) -> DashboardService:
    ranking_service = CandidateRankingService(
        campaign_repo=CampaignRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        candidate_repo=CandidateRepository(db),
        job_description_repo=JobDescriptionRepository(db),
        scoring_rule_service=ScoringRuleService(ScoringRuleRepository(db), CampaignRepository(db)),
    )
    return DashboardService(
        repo=DashboardRepository(db),
        candidate_repo=CandidateRepository(db),
        ranking_service=ranking_service,
    )


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]

# Dashboard exposes org-wide recruiting data; candidates have no legitimate use for it.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Aggregate recruiting metrics for the current organization",
    responses={
        200: {"description": "Campaign, candidate, and match-score summary."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_summary(
    service: DashboardServiceDep,
    current_user: RecruiterUser,
) -> DashboardSummaryResponse:
    return await service.get_summary(current_user)


@router.get(
    "/recent-campaigns",
    response_model=list[RecentCampaignResponse],
    summary="Most recently created campaigns",
    responses={
        200: {"description": "Campaigns ordered by creation date, most recent first."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_recent_campaigns(
    service: DashboardServiceDep,
    current_user: RecruiterUser,
    limit: int = Query(5, ge=1, le=50, description="Maximum campaigns to return"),
) -> list[RecentCampaignResponse]:
    return await service.get_recent_campaigns(current_user, limit=limit)


@router.get(
    "/top-candidates",
    response_model=list[TopCandidateResponse],
    summary="Highest-ranked candidates across active campaigns",
    responses={
        200: {
            "description": (
                "Candidates ranked live against each active campaign's job description, "
                "highest match score first. Campaigns without a ranking-ready job "
                "description are skipped."
            )
        },
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_top_candidates(
    service: DashboardServiceDep,
    current_user: RecruiterUser,
    limit: int = Query(10, ge=1, le=50, description="Maximum candidates to return"),
) -> list[TopCandidateResponse]:
    return await service.get_top_candidates(current_user, limit=limit)


@router.get(
    "/processing-status",
    response_model=ProcessingStatusResponse,
    summary="Background processing pipeline counters",
    responses={
        200: {"description": "Parsing/embedding queue depths and job outcome counts."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_processing_status(
    service: DashboardServiceDep,
    current_user: RecruiterUser,
) -> ProcessingStatusResponse:
    return await service.get_processing_status(current_user)


@router.get(
    "/activity",
    response_model=list[ActivityItemResponse],
    summary="Recent recruiter activity feed",
    responses={
        200: {"description": "Recent events, newest first."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "User has no organization."},
    },
)
async def get_activity(
    service: DashboardServiceDep,
    current_user: RecruiterUser,
    limit: int = Query(20, ge=1, le=100, description="Maximum events to return"),
) -> list[ActivityItemResponse]:
    return await service.get_activity(current_user, limit=limit)

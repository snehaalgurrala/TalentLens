import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DBSession, RequireRoles
from app.models.campaign import Campaign, CampaignPriority, CampaignStatus, EmploymentType
from app.models.user import User, UserRole
from app.models.resume_file import PipelineStage, ReviewStatus
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.job_description import JobDescriptionRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.repositories.user import UserRepository
from app.schemas.campaign import (
    CampaignCreate,
    CampaignProcessingStatusResponse,
    CampaignResponse,
    CampaignSummaryResponse,
    CampaignUpdate,
)
from app.schemas.candidate_management import CandidateListResponse
from app.services.campaign import CampaignService
from app.services.campaign_summary import CampaignSummaryService
from app.services.candidate_management import CandidateManagementService
from app.services.candidate_ranking import CandidateRankingService
from app.services.scoring_rule import ScoringRuleService

router = APIRouter()

# ── Dependency factories (overridable in tests) ───────────────────────────────


def get_campaign_service(db: DBSession) -> CampaignService:
    return CampaignService(CampaignRepository(db))


CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]


def get_campaign_summary_service(db: DBSession) -> CampaignSummaryService:
    ranking_service = CandidateRankingService(
        campaign_repo=CampaignRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        candidate_repo=CandidateRepository(db),
        job_description_repo=JobDescriptionRepository(db),
        scoring_rule_service=ScoringRuleService(ScoringRuleRepository(db), CampaignRepository(db)),
    )
    return CampaignSummaryService(CampaignRepository(db), ranking_service)


CampaignSummaryServiceDep = Annotated[
    CampaignSummaryService, Depends(get_campaign_summary_service)
]


def get_candidate_management_service(db: DBSession) -> CandidateManagementService:
    ranking_service = CandidateRankingService(
        campaign_repo=CampaignRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        candidate_repo=CandidateRepository(db),
        job_description_repo=JobDescriptionRepository(db),
        scoring_rule_service=ScoringRuleService(ScoringRuleRepository(db), CampaignRepository(db)),
    )
    return CandidateManagementService(
        resume_file_repo=ResumeFileRepository(db),
        candidate_repo=CandidateRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        campaign_repo=CampaignRepository(db),
        user_repo=UserRepository(db),
        ranking_service=ranking_service,
    )


CandidateManagementServiceDep = Annotated[
    CandidateManagementService, Depends(get_candidate_management_service)
]

# Candidates cannot create, modify, or delete campaigns.
_require_write_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
WriteUser = Annotated[User, Depends(_require_write_role)]

# Summary/processing-status expose internal pipeline detail; candidates have no use for it.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


def _to_response(campaign: Campaign, resume_count: int = 0, processing_count: int = 0) -> CampaignResponse:
    response = CampaignResponse.model_validate(campaign)
    return response.model_copy(
        update={"resume_count": resume_count, "processing_resume_count": processing_count}
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recruitment campaign",
    responses={
        201: {"description": "Campaign created successfully."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        422: {"description": "Validation error or user has no organization."},
    },
)
async def create_campaign(
    data: CampaignCreate,
    service: CampaignServiceDep,
    current_user: WriteUser,
) -> CampaignResponse:
    campaign = await service.create(data, current_user)
    return _to_response(campaign)


@router.get(
    "/",
    response_model=list[CampaignResponse],
    summary="List campaigns for the authenticated user's organization",
    responses={
        200: {"description": "Filtered, paginated list of campaigns."},
        422: {"description": "User has no organization."},
    },
)
async def list_campaigns(
    service: CampaignServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    search: str | None = Query(None, description="Matches campaign name or job title"),
    status_filter: CampaignStatus | None = Query(None, alias="status"),
    department: str | None = Query(None, description="Partial, case-insensitive match"),
    employment_type: EmploymentType | None = Query(None),
    priority: CampaignPriority | None = Query(None),
    recruiter_id: uuid.UUID | None = Query(None),
    hiring_manager_id: uuid.UUID | None = Query(None),
    created_after: date | None = Query(None),
    created_before: date | None = Query(None),
    sort_by: Literal["created_at", "updated_at", "title", "status", "priority"] = Query(
        "created_at"
    ),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
) -> list[CampaignResponse]:
    rows = await service.list_campaigns(
        current_user,
        skip=skip,
        limit=limit,
        search=search,
        status_filter=status_filter,
        department=department,
        employment_type=employment_type,
        priority=priority,
        recruiter_id=recruiter_id,
        hiring_manager_id=hiring_manager_id,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return [_to_response(campaign, resume_count, processing_count) for campaign, resume_count, processing_count in rows]


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get a single campaign by ID",
    responses={
        200: {"description": "Campaign details."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def get_campaign(
    campaign_id: uuid.UUID,
    service: CampaignServiceDep,
    current_user: CurrentUser,
) -> CampaignResponse:
    campaign = await service.get(campaign_id, current_user)
    return _to_response(campaign)


@router.get(
    "/{campaign_id}/summary",
    response_model=CampaignSummaryResponse,
    summary="Get candidate-pipeline summary metrics for a campaign",
    responses={
        200: {"description": "Summary counts for the campaign's detail page."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def get_campaign_summary(
    campaign_id: uuid.UUID,
    campaign_service: CampaignServiceDep,
    summary_service: CampaignSummaryServiceDep,
    current_user: RecruiterUser,
) -> CampaignSummaryResponse:
    await campaign_service.get(campaign_id, current_user)  # 404 if not found / wrong org
    return await summary_service.get_summary(campaign_id, current_user)


@router.get(
    "/{campaign_id}/processing-status",
    response_model=CampaignProcessingStatusResponse,
    summary="Get resume-processing pipeline stage counts for a campaign",
    responses={
        200: {"description": "Per-stage counts for the processing monitor."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def get_campaign_processing_status(
    campaign_id: uuid.UUID,
    campaign_service: CampaignServiceDep,
    summary_service: CampaignSummaryServiceDep,
    current_user: RecruiterUser,
) -> CampaignProcessingStatusResponse:
    await campaign_service.get(campaign_id, current_user)  # 404 if not found / wrong org
    return await summary_service.get_processing_status(campaign_id, current_user)


@router.get(
    "/{campaign_id}/candidates",
    response_model=CandidateListResponse,
    summary="List candidates applied to a campaign, with ranking, pipeline, and search/filter support",
    responses={
        200: {
            "description": (
                "Paginated candidate list. ranking_available=false when the campaign has no "
                "job description ready to rank against yet — score fields are null in that case."
            )
        },
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def list_campaign_candidates(
    campaign_id: uuid.UUID,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
    search: str | None = Query(None, description="Matches name, email, phone, company, skills, college"),
    pipeline_stage: PipelineStage | None = Query(None),
    review_status: ReviewStatus | None = Query(None),
    assigned_recruiter_id: uuid.UUID | None = Query(None),
    sort_by: Literal["overall_score", "candidate_name", "applied_at", "years_of_experience"] = Query(
        "overall_score"
    ),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> CandidateListResponse:
    return await service.list_campaign_candidates(
        campaign_id,
        current_user,
        search=search,
        pipeline_stage=pipeline_stage,
        review_status=review_status,
        assigned_recruiter_id=assigned_recruiter_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        skip=skip,
        limit=limit,
    )


@router.patch(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update a campaign (partial update)",
    responses={
        200: {"description": "Updated campaign."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found."},
    },
)
async def update_campaign(
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    service: CampaignServiceDep,
    current_user: WriteUser,
) -> CampaignResponse:
    campaign = await service.update(campaign_id, data, current_user)
    return _to_response(campaign)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a campaign",
    responses={
        204: {"description": "Campaign deleted (soft)."},
        403: {"description": "Insufficient role or not the campaign owner."},
        404: {"description": "Campaign not found."},
    },
)
async def delete_campaign(
    campaign_id: uuid.UUID,
    service: CampaignServiceDep,
    current_user: WriteUser,
) -> None:
    await service.delete(campaign_id, current_user)

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.job_description import JobDescriptionRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.repositories.user import UserRepository
from app.schemas.candidate_management import (
    BulkActionRequest,
    BulkActionResult,
    BulkAssignRecruiterRequest,
    NotesUpdate,
    PipelineStageUpdate,
    RecruiterAssignmentUpdate,
)
from app.schemas.resume_file import ResumeFileResponse
from app.services.candidate_management import CandidateManagementService
from app.services.candidate_ranking import CandidateRankingService
from app.services.scoring_rule import ScoringRuleService

router = APIRouter()


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

# Candidates cannot review/manage other candidates.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


# ── Bulk actions ──────────────────────────────────────────────────────────────
# Declared before the /{resume_file_id}/... routes below so "bulk" in the path
# is never captured as a resume_file_id path parameter.


@router.post(
    "/bulk/shortlist",
    response_model=BulkActionResult,
    summary="Shortlist multiple candidates",
)
async def bulk_shortlist(
    data: BulkActionRequest,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> BulkActionResult:
    return await service.bulk_shortlist(data.resume_file_ids, current_user)


@router.post(
    "/bulk/reject",
    response_model=BulkActionResult,
    summary="Reject multiple candidates",
)
async def bulk_reject(
    data: BulkActionRequest,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> BulkActionResult:
    return await service.bulk_reject(data.resume_file_ids, current_user)


@router.post(
    "/bulk/assign-recruiter",
    response_model=BulkActionResult,
    summary="Assign a recruiter to multiple candidates",
)
async def bulk_assign_recruiter(
    data: BulkAssignRecruiterRequest,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> BulkActionResult:
    return await service.bulk_assign_recruiter(
        data.resume_file_ids, data.assigned_recruiter_id, current_user
    )


@router.post(
    "/bulk/delete",
    response_model=BulkActionResult,
    summary="Soft-delete multiple candidates' applications",
)
async def bulk_delete(
    data: BulkActionRequest,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> BulkActionResult:
    return await service.bulk_delete(data.resume_file_ids, current_user)


# ── Single-record actions ──────────────────────────────────────────────────────


@router.patch(
    "/{resume_file_id}/pipeline-stage",
    response_model=ResumeFileResponse,
    summary="Move a candidate to a different pipeline stage",
)
async def update_pipeline_stage(
    resume_file_id: uuid.UUID,
    data: PipelineStageUpdate,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> ResumeFileResponse:
    rf = await service.update_pipeline_stage(resume_file_id, data.pipeline_stage, current_user)
    return ResumeFileResponse.model_validate(rf)


@router.patch(
    "/{resume_file_id}/recruiter",
    response_model=ResumeFileResponse,
    summary="Assign (or unassign) a recruiter to a candidate",
)
async def assign_recruiter(
    resume_file_id: uuid.UUID,
    data: RecruiterAssignmentUpdate,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> ResumeFileResponse:
    rf = await service.assign_recruiter(resume_file_id, data.assigned_recruiter_id, current_user)
    return ResumeFileResponse.model_validate(rf)


@router.patch(
    "/{resume_file_id}/notes",
    response_model=ResumeFileResponse,
    summary="Set (or clear) a recruiter's notes on a candidate",
)
async def update_notes(
    resume_file_id: uuid.UUID,
    data: NotesUpdate,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> ResumeFileResponse:
    rf = await service.update_notes(resume_file_id, data.notes, current_user)
    return ResumeFileResponse.model_validate(rf)


@router.post(
    "/{resume_file_id}/shortlist",
    response_model=ResumeFileResponse,
    summary="Shortlist a candidate",
)
async def shortlist_candidate(
    resume_file_id: uuid.UUID,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> ResumeFileResponse:
    rf = await service.shortlist(resume_file_id, current_user)
    return ResumeFileResponse.model_validate(rf)


@router.post(
    "/{resume_file_id}/reject",
    response_model=ResumeFileResponse,
    summary="Reject a candidate",
)
async def reject_candidate(
    resume_file_id: uuid.UUID,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> ResumeFileResponse:
    rf = await service.reject(resume_file_id, current_user)
    return ResumeFileResponse.model_validate(rf)


@router.delete(
    "/{resume_file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a candidate's application",
)
async def delete_candidate(
    resume_file_id: uuid.UUID,
    service: CandidateManagementServiceDep,
    current_user: RecruiterUser,
) -> None:
    await service.delete(resume_file_id, current_user)

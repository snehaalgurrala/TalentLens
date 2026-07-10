import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.candidate_activity import CandidateActivityRepository
from app.repositories.candidate_note import CandidateNoteRepository
from app.repositories.candidate_task import CandidateTaskRepository
from app.repositories.job_description import JobDescriptionRepository
from app.repositories.parsed_resume import ParsedResumeRepository
from app.repositories.platform_ai_config import PlatformAIConfigRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.scoring_rule import ScoringRuleRepository
from app.repositories.user import UserRepository
from app.schemas.candidate_activity import CandidateActivityResponse
from app.schemas.candidate_note import (
    CandidateNoteCreate,
    CandidateNotePinUpdate,
    CandidateNoteResponse,
    CandidateNoteUpdate,
)
from app.schemas.candidate_profile import CandidateMatchAnalysisResponse, CandidateProfileResponse
from app.schemas.candidate_task import (
    CandidateTaskCreate,
    CandidateTaskReassign,
    CandidateTaskResponse,
    CandidateTaskUpdate,
)
from app.schemas.user import UserSummaryResponse
from app.services.candidate_activity import CandidateActivityService
from app.services.candidate_note import CandidateNoteService
from app.services.candidate_profile import CandidateProfileService
from app.services.candidate_ranking import CandidateRankingService
from app.services.candidate_task import CandidateTaskService
from app.services.scoring_rule import ScoringRuleService

router = APIRouter()

# Rankings/notes/activity expose internal recruiter workflow; candidates have no legitimate use for it.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]


# ── Dependency factories (overridable in tests) ───────────────────────────────


def get_candidate_profile_service(db: DBSession) -> CandidateProfileService:
    ranking_service = CandidateRankingService(
        campaign_repo=CampaignRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        candidate_repo=CandidateRepository(db),
        job_description_repo=JobDescriptionRepository(db),
        scoring_rule_service=ScoringRuleService(ScoringRuleRepository(db), CampaignRepository(db)),
    )
    return CandidateProfileService(
        resume_file_repo=ResumeFileRepository(db),
        candidate_repo=CandidateRepository(db),
        parsed_resume_repo=ParsedResumeRepository(db),
        campaign_repo=CampaignRepository(db),
        user_repo=UserRepository(db),
        activity_repo=CandidateActivityRepository(db),
        ranking_service=ranking_service,
        platform_ai_config_repo=PlatformAIConfigRepository(db),
    )


CandidateProfileServiceDep = Annotated[
    CandidateProfileService, Depends(get_candidate_profile_service)
]


def get_candidate_note_service(db: DBSession) -> CandidateNoteService:
    return CandidateNoteService(
        note_repo=CandidateNoteRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        candidate_repo=CandidateRepository(db),
        campaign_repo=CampaignRepository(db),
        activity_repo=CandidateActivityRepository(db),
    )


CandidateNoteServiceDep = Annotated[CandidateNoteService, Depends(get_candidate_note_service)]


def get_candidate_activity_service(db: DBSession) -> CandidateActivityService:
    return CandidateActivityService(
        activity_repo=CandidateActivityRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        candidate_repo=CandidateRepository(db),
        campaign_repo=CampaignRepository(db),
    )


CandidateActivityServiceDep = Annotated[
    CandidateActivityService, Depends(get_candidate_activity_service)
]


def get_candidate_task_service(db: DBSession) -> CandidateTaskService:
    return CandidateTaskService(
        task_repo=CandidateTaskRepository(db),
        resume_file_repo=ResumeFileRepository(db),
        candidate_repo=CandidateRepository(db),
        campaign_repo=CampaignRepository(db),
        activity_repo=CandidateActivityRepository(db),
        user_repo=UserRepository(db),
    )


CandidateTaskServiceDep = Annotated[CandidateTaskService, Depends(get_candidate_task_service)]


def _note_to_response(note, current_user: User) -> CandidateNoteResponse:
    """For notes freshly created/edited by the caller, the author is always
    the acting user — build the response from it directly rather than
    touching the ORM `author` relationship (which isn't populated on a
    just-flushed row)."""
    author = (
        current_user
        if note.author_id == current_user.id
        else note.author
    )
    return CandidateNoteResponse(
        id=note.id,
        resume_file_id=note.resume_file_id,
        author=UserSummaryResponse.model_validate(author) if author else None,
        body=note.body,
        created_at=note.created_at,
        updated_at=note.updated_at,
        can_edit=note.author_id == current_user.id,
        is_pinned=bool(note.is_pinned),
        mentioned_user_ids=list(note.mentioned_user_ids or []),
    )


# ── Profile / match analysis ──────────────────────────────────────────────────


@router.get(
    "/{id}/profile",
    response_model=CandidateProfileResponse,
    summary="Get a candidate's full profile",
)
async def get_candidate_profile(
    id: uuid.UUID,
    service: CandidateProfileServiceDep,
    current_user: RecruiterUser,
) -> CandidateProfileResponse:
    return await service.get_profile(id, current_user)


@router.get(
    "/{id}/match-analysis",
    response_model=CandidateMatchAnalysisResponse,
    summary="Get a candidate's detailed AI match analysis",
    responses={
        422: {
            "description": (
                "Candidate has not been ranked yet (job description or resume "
                "still parsing/embedding)."
            )
        },
    },
)
async def get_candidate_match_analysis(
    id: uuid.UUID,
    service: CandidateProfileServiceDep,
    current_user: RecruiterUser,
) -> CandidateMatchAnalysisResponse:
    return await service.get_match_analysis(id, current_user)


# ── Notes ─────────────────────────────────────────────────────────────────────


@router.get(
    "/{id}/notes",
    response_model=list[CandidateNoteResponse],
    summary="List notes on a candidate",
)
async def list_candidate_notes(
    id: uuid.UUID,
    service: CandidateNoteServiceDep,
    current_user: RecruiterUser,
) -> list[CandidateNoteResponse]:
    notes = await service.list(id, current_user)
    return [_note_to_response(n, current_user) for n in notes]


@router.post(
    "/{id}/notes",
    response_model=CandidateNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a note to a candidate",
)
async def create_candidate_note(
    id: uuid.UUID,
    data: CandidateNoteCreate,
    service: CandidateNoteServiceDep,
    current_user: RecruiterUser,
) -> CandidateNoteResponse:
    note = await service.create(id, data.body, current_user, data.mentioned_user_ids)
    return _note_to_response(note, current_user)


@router.patch(
    "/{id}/notes/{note_id}",
    response_model=CandidateNoteResponse,
    summary="Edit your own note on a candidate",
)
async def update_candidate_note(
    id: uuid.UUID,
    note_id: uuid.UUID,
    data: CandidateNoteUpdate,
    service: CandidateNoteServiceDep,
    current_user: RecruiterUser,
) -> CandidateNoteResponse:
    note = await service.update(id, note_id, data.body, current_user, data.mentioned_user_ids)
    return _note_to_response(note, current_user)


@router.patch(
    "/{id}/notes/{note_id}/pin",
    response_model=CandidateNoteResponse,
    summary="Pin or unpin a note",
)
async def pin_candidate_note(
    id: uuid.UUID,
    note_id: uuid.UUID,
    data: CandidateNotePinUpdate,
    service: CandidateNoteServiceDep,
    current_user: RecruiterUser,
) -> CandidateNoteResponse:
    note = await service.pin(id, note_id, data.is_pinned, current_user)
    return _note_to_response(note, current_user)


@router.delete(
    "/{id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete your own note on a candidate",
)
async def delete_candidate_note(
    id: uuid.UUID,
    note_id: uuid.UUID,
    service: CandidateNoteServiceDep,
    current_user: RecruiterUser,
) -> None:
    await service.delete(id, note_id, current_user)


# ── Activity ──────────────────────────────────────────────────────────────────


@router.get(
    "/{id}/activity",
    response_model=list[CandidateActivityResponse],
    summary="Get a candidate's activity timeline",
)
async def list_candidate_activity(
    id: uuid.UUID,
    service: CandidateActivityServiceDep,
    current_user: RecruiterUser,
) -> list[CandidateActivityResponse]:
    return await service.list(id, current_user)


# ── Tasks ─────────────────────────────────────────────────────────────────────


@router.get(
    "/{id}/tasks",
    response_model=list[CandidateTaskResponse],
    summary="List tasks on a candidate",
)
async def list_candidate_tasks(
    id: uuid.UUID,
    service: CandidateTaskServiceDep,
    current_user: RecruiterUser,
) -> list[CandidateTaskResponse]:
    tasks = await service.list(id, current_user)
    return [CandidateTaskResponse.model_validate(t) for t in tasks]


@router.post(
    "/{id}/tasks",
    response_model=CandidateTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task on a candidate",
)
async def create_candidate_task(
    id: uuid.UUID,
    data: CandidateTaskCreate,
    service: CandidateTaskServiceDep,
    current_user: RecruiterUser,
) -> CandidateTaskResponse:
    task = await service.create(id, data, current_user)
    return CandidateTaskResponse.model_validate(task)


@router.patch(
    "/{id}/tasks/{task_id}",
    response_model=CandidateTaskResponse,
    summary="Edit a task on a candidate",
)
async def update_candidate_task(
    id: uuid.UUID,
    task_id: uuid.UUID,
    data: CandidateTaskUpdate,
    service: CandidateTaskServiceDep,
    current_user: RecruiterUser,
) -> CandidateTaskResponse:
    task = await service.update(id, task_id, data, current_user)
    return CandidateTaskResponse.model_validate(task)


@router.post(
    "/{id}/tasks/{task_id}/complete",
    response_model=CandidateTaskResponse,
    summary="Mark a task complete",
)
async def complete_candidate_task(
    id: uuid.UUID,
    task_id: uuid.UUID,
    service: CandidateTaskServiceDep,
    current_user: RecruiterUser,
) -> CandidateTaskResponse:
    task = await service.complete(id, task_id, current_user)
    return CandidateTaskResponse.model_validate(task)


@router.patch(
    "/{id}/tasks/{task_id}/reassign",
    response_model=CandidateTaskResponse,
    summary="Reassign a task to a different org member",
)
async def reassign_candidate_task(
    id: uuid.UUID,
    task_id: uuid.UUID,
    data: CandidateTaskReassign,
    service: CandidateTaskServiceDep,
    current_user: RecruiterUser,
) -> CandidateTaskResponse:
    task = await service.reassign(id, task_id, data.assignee_id, current_user)
    return CandidateTaskResponse.model_validate(task)


@router.delete(
    "/{id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task on a candidate",
)
async def delete_candidate_task(
    id: uuid.UUID,
    task_id: uuid.UUID,
    service: CandidateTaskServiceDep,
    current_user: RecruiterUser,
) -> None:
    await service.delete(id, task_id, current_user)

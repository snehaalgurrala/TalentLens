import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile, status

from app.api.deps import DBSession, RequireRoles
from app.models.assessment_recording import RecordingType
from app.models.user import User, UserRole
from app.repositories.assessment_answer import AssessmentAnswerRepository
from app.repositories.assessment_recording import AssessmentRecordingRepository
from app.repositories.assessment_session import AssessmentSessionRepository
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.schemas.assessment_session import (
    AssessmentAnswerCreate,
    AssessmentAnswerResponse,
    AssessmentRecordingCreate,
    AssessmentRecordingResponse,
    AssessmentSessionCreate,
    AssessmentSessionProgressUpdate,
    AssessmentSessionResponse,
)
from app.services.assessment_session import AssessmentSessionService
from app.storage.base import StorageBackend as StorageBackendType
from app.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

router = APIRouter()

# Candidates have no platform account/token in this sprint — every call here
# is made on a candidate's behalf by an org member, same access model as
# candidate_profile.py's notes/tasks/activity endpoints.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]
StorageDep = Annotated[StorageBackendType, Depends(get_storage_backend)]


def get_assessment_session_service(
    db: DBSession, storage: StorageDep
) -> AssessmentSessionService:
    return AssessmentSessionService(
        session_repo=AssessmentSessionRepository(db),
        answer_repo=AssessmentAnswerRepository(db),
        recording_repo=AssessmentRecordingRepository(db),
        campaign_repo=CampaignRepository(db),
        candidate_repo=CandidateRepository(db),
        storage=storage,
    )


AssessmentSessionServiceDep = Annotated[
    AssessmentSessionService, Depends(get_assessment_session_service)
]


def _enqueue_transcription(recording_id: str) -> None:
    """Dispatch a background transcription task. Lazy import avoids Celery at module import time."""
    from app.workers.speech_transcription import transcribe_recording as _task  # noqa: PLC0415

    _task.delay(recording_id)


@router.post(
    "",
    response_model=AssessmentSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create (or resume) a candidate's assessment session for a campaign",
    responses={
        201: {"description": "Session created or an existing in-progress/completed one returned."},
        404: {"description": "Campaign or candidate not found in your organization."},
    },
)
async def create_assessment_session(
    data: AssessmentSessionCreate,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
) -> AssessmentSessionResponse:
    assessment_session = await service.create_or_resume(data, current_user)
    return AssessmentSessionResponse.model_validate(assessment_session)


@router.get(
    "/{id}",
    response_model=AssessmentSessionResponse,
    summary="Get an assessment session",
    responses={404: {"description": "Assessment session not found."}},
)
async def get_assessment_session(
    id: uuid.UUID,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
) -> AssessmentSessionResponse:
    assessment_session = await service.get_session(id, current_user)
    return AssessmentSessionResponse.model_validate(assessment_session)


@router.patch(
    "/{id}",
    response_model=AssessmentSessionResponse,
    summary="Update a session's current section/question progress",
    responses={
        404: {"description": "Assessment session not found."},
        422: {"description": "Session already completed."},
    },
)
async def update_assessment_session(
    id: uuid.UUID,
    data: AssessmentSessionProgressUpdate,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
) -> AssessmentSessionResponse:
    assessment_session = await service.update_progress(id, data, current_user)
    return AssessmentSessionResponse.model_validate(assessment_session)


@router.post(
    "/{id}/answers",
    response_model=AssessmentAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save (upsert) an aptitude answer",
    responses={
        404: {"description": "Assessment session not found."},
        422: {"description": "Session already completed."},
    },
)
async def save_assessment_answer(
    id: uuid.UUID,
    data: AssessmentAnswerCreate,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
) -> AssessmentAnswerResponse:
    answer = await service.save_answer(id, data, current_user)
    return AssessmentAnswerResponse.model_validate(answer)


@router.post(
    "/{id}/recordings",
    response_model=AssessmentRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save (upsert) recording metadata (no audio bytes in this sprint)",
    responses={
        404: {"description": "Assessment session not found."},
        422: {"description": "Session already completed."},
    },
)
async def save_assessment_recording(
    id: uuid.UUID,
    data: AssessmentRecordingCreate,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
) -> AssessmentRecordingResponse:
    recording = await service.save_recording(id, data, current_user)
    return AssessmentRecordingResponse.model_validate(recording)


@router.post(
    "/{id}/recordings/{recording_type}/upload",
    response_model=AssessmentRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload the audio bytes for a recording and mark it UPLOADED",
    responses={
        404: {"description": "Assessment session not found."},
        422: {
            "description": (
                "Session already completed, unsupported mime type, oversized file, "
                "or missing/empty upload."
            )
        },
    },
)
async def upload_assessment_recording(
    id: uuid.UUID,
    recording_type: RecordingType,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
    file: UploadFile,
    duration_seconds: Annotated[float, Form(gt=0)],
) -> AssessmentRecordingResponse:
    recording = await service.upload_recording(
        id, recording_type, file, duration_seconds, current_user
    )
    logger.info(
        "Dispatching transcription task",
        extra={"recording_id": str(recording.id), "recording_type": recording_type.value},
    )
    _enqueue_transcription(str(recording.id))
    return AssessmentRecordingResponse.model_validate(recording)


@router.post(
    "/{id}/complete",
    response_model=AssessmentSessionResponse,
    summary="Mark a session complete (idempotent)",
    responses={404: {"description": "Assessment session not found."}},
)
async def complete_assessment_session(
    id: uuid.UUID,
    service: AssessmentSessionServiceDep,
    current_user: RecruiterUser,
) -> AssessmentSessionResponse:
    assessment_session = await service.complete_session(id, current_user)
    return AssessmentSessionResponse.model_validate(assessment_session)

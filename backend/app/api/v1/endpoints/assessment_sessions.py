import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer

from app.api.deps import DBSession, RequireRoles
from app.core.security import decode_token, hash_token
from app.models.assessment_invitation import AssessmentInvitationStatus
from app.models.assessment_recording import RecordingType
from app.models.user import User, UserRole
from app.repositories.assessment_analysis import AssessmentAnalysisRepository
from app.repositories.assessment_answer import AssessmentAnswerRepository
from app.repositories.assessment_invitation import AssessmentInvitationRepository
from app.repositories.assessment_recording import AssessmentRecordingRepository
from app.repositories.assessment_session import AssessmentSessionRepository
from app.repositories.assessment_transcript import AssessmentTranscriptRepository
from app.repositories.campaign import CampaignRepository
from app.repositories.candidate import CandidateRepository
from app.repositories.communication_assessment import CommunicationAssessmentRepository
from app.repositories.resume_file import ResumeFileRepository
from app.repositories.user import UserRepository
from app.schemas.assessment_dashboard import (
    AssessmentSessionFullResponse,
    AssessmentSessionListResponse,
)
from app.schemas.assessment_session import (
    AssessmentAnswerCreate,
    AssessmentAnswerResponse,
    AssessmentRecordingCreate,
    AssessmentRecordingResponse,
    AssessmentSessionCreate,
    AssessmentSessionProgressUpdate,
    AssessmentSessionResponse,
)
from app.services.assessment_dashboard import AssessmentDashboardService
from app.services.assessment_session import AssessmentSessionService
from app.storage.base import StorageBackend as StorageBackendType
from app.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

router = APIRouter()

# Every endpoint here except the recording upload is recruiter-authenticated
# only — every call is made on a candidate's behalf by an org member, same
# access model as candidate_profile.py's notes/tasks/activity endpoints.
_require_recruiter_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
RecruiterUser = Annotated[User, Depends(_require_recruiter_role)]
StorageDep = Annotated[StorageBackendType, Depends(get_storage_backend)]

# auto_error=False: unlike the shared oauth2_scheme in api/deps.py, a missing
# bearer token here is not fatal — resolve_recording_upload_org_id falls back
# to the candidate's invitation token instead.
_optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_TERMINAL_INVITATION_STATUSES = (
    AssessmentInvitationStatus.EXPIRED,
    AssessmentInvitationStatus.REVOKED,
    AssessmentInvitationStatus.COMPLETED,
)


async def resolve_recording_upload_org_id(
    id: uuid.UUID,
    db: DBSession,
    token: Annotated[str | None, Depends(_optional_oauth2_scheme)] = None,
    x_assessment_token: Annotated[str | None, Header(alias="X-Assessment-Token")] = None,
) -> uuid.UUID:
    """Authorizes the one call a candidate's own browser makes directly —
    recording upload — via either a recruiter/admin JWT (existing
    dev-testing path through landing-screen.tsx, unchanged) or the
    candidate's own invitation token scoped to this exact session
    (candidates have no platform account, so there is no JWT to check for
    that path)."""
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") == "access":
                user = await UserRepository(db).get_by_id(uuid.UUID(payload["sub"]))
                if (
                    user is not None
                    and user.is_active
                    and user.role in {UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN}
                    and user.org_id is not None
                ):
                    return user.org_id
        except (jwt.InvalidTokenError, ValueError, KeyError):
            pass

    if x_assessment_token:
        invitation = await AssessmentInvitationRepository(db).get_by_token_hash(
            hash_token(x_assessment_token)
        )
        if (
            invitation is not None
            and invitation.assessment_session_id == id
            and invitation.status not in _TERMINAL_INVITATION_STATUSES
            and invitation.expires_at >= datetime.now(UTC)
        ):
            return invitation.organization_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authorized for this assessment session.",
    )


def get_assessment_dashboard_service(db: DBSession) -> AssessmentDashboardService:
    return AssessmentDashboardService(
        session_repo=AssessmentSessionRepository(db),
        recording_repo=AssessmentRecordingRepository(db),
        transcript_repo=AssessmentTranscriptRepository(db),
        analysis_repo=AssessmentAnalysisRepository(db),
        communication_assessment_repo=CommunicationAssessmentRepository(db),
        campaign_repo=CampaignRepository(db),
        candidate_repo=CandidateRepository(db),
        resume_file_repo=ResumeFileRepository(db),
    )


AssessmentDashboardServiceDep = Annotated[
    AssessmentDashboardService, Depends(get_assessment_dashboard_service)
]


def _content_disposition(filename: str) -> str:
    """Build a Content-Disposition header value safe against header-injection
    and non-ASCII filenames (RFC 5987 fallback via filename*). Mirrors
    resumes.py's helper of the same name."""
    from urllib.parse import quote

    safe = re.sub(r"[\r\n\"]", "_", filename)
    return f'attachment; filename="{safe}"; filename*=UTF-8\'\'{quote(filename)}'


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
    "",
    response_model=AssessmentSessionListResponse,
    summary="List assessment sessions for the organization (optionally filtered by campaign)",
)
async def list_assessment_sessions(
    service: AssessmentDashboardServiceDep,
    current_user: RecruiterUser,
    campaign_id: uuid.UUID | None = None,
) -> AssessmentSessionListResponse:
    return await service.list_sessions(current_user, campaign_id)


@router.get(
    "/by-candidate/{candidate_id}",
    response_model=AssessmentSessionResponse,
    summary="Look up a candidate's assessment session for a campaign (read-only)",
    responses={404: {"description": "Campaign, candidate, or assessment session not found."}},
)
async def get_assessment_session_by_candidate(
    candidate_id: uuid.UUID,
    campaign_id: uuid.UUID,
    service: AssessmentDashboardServiceDep,
    current_user: RecruiterUser,
) -> AssessmentSessionResponse:
    """Registered before GET /{id} so the literal 'by-candidate' segment isn't
    swallowed by the {id}: UUID path parameter."""
    assessment_session = await service.get_session_by_candidate(
        candidate_id, campaign_id, current_user
    )
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


@router.get(
    "/{id}/full",
    response_model=AssessmentSessionFullResponse,
    summary="Get the full recruiter-facing assessment dashboard payload for a session",
    responses={404: {"description": "Assessment session not found."}},
)
async def get_assessment_session_full(
    id: uuid.UUID,
    service: AssessmentDashboardServiceDep,
    current_user: RecruiterUser,
) -> AssessmentSessionFullResponse:
    return await service.get_full(id, current_user)


@router.get(
    "/{id}/recordings/{recording_type}/download",
    summary="Download a recording's audio bytes",
    responses={
        200: {"description": "Raw audio bytes with the recording's original MIME type."},
        404: {"description": "Assessment session or recording not found."},
    },
)
async def download_assessment_recording(
    id: uuid.UUID,
    recording_type: RecordingType,
    service: AssessmentDashboardServiceDep,
    storage: StorageDep,
    current_user: RecruiterUser,
) -> Response:
    recording = await service.get_recording_audio(id, recording_type, current_user)
    data = await storage.load(recording.storage_path)
    return Response(
        content=data,
        media_type=recording.mime_type,
        headers={"Content-Disposition": _content_disposition(recording.filename)},
    )


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
        401: {
            "description": (
                "Neither a valid recruiter/admin session nor a live invitation token "
                "scoped to this session was provided."
            )
        },
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
    org_id: Annotated[uuid.UUID, Depends(resolve_recording_upload_org_id)],
    file: UploadFile,
    duration_seconds: Annotated[float, Form(gt=0)],
) -> AssessmentRecordingResponse:
    recording = await service.upload_recording(
        id, recording_type, file, duration_seconds, org_id
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

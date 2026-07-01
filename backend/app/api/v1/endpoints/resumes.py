import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status

from app.api.deps import CurrentUser, DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.resume_file import ResumeFileRepository
from app.schemas.resume_file import ResumeFileResponse, UploadResponse
from app.services.resume_file import ResumeFileService
from app.storage.base import StorageBackend as StorageBackendType
from app.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

router = APIRouter()

_require_write_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
WriteUser = Annotated[User, Depends(_require_write_role)]
StorageDep = Annotated[StorageBackendType, Depends(get_storage_backend)]


def get_resume_service(db: DBSession, storage: StorageDep) -> ResumeFileService:
    return ResumeFileService(
        ResumeFileRepository(db),
        CampaignRepository(db),
        storage,
    )


ResumeServiceDep = Annotated[ResumeFileService, Depends(get_resume_service)]


def _enqueue_parse(resume_file_id: str) -> None:
    """Dispatch a background parse task. Lazy import avoids Celery at module import time."""
    from app.workers.resume_parser import parse_resume as _task  # noqa: PLC0415

    _task.delay(resume_file_id)


@router.post(
    "/campaigns/{campaign_id}/resumes/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload resume files to a campaign",
    responses={
        201: {"description": "Files uploaded and background parsing queued."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
        422: {"description": "Unsupported file type, file too large, or invalid ZIP."},
    },
)
async def upload_resumes(
    campaign_id: uuid.UUID,
    files: list[UploadFile],
    service: ResumeServiceDep,
    current_user: WriteUser,
) -> UploadResponse:
    uploaded = await service.upload(campaign_id, files, current_user)

    for rf in uploaded:
        logger.info(
            "Dispatching parse task",
            extra={"resume_file_id": str(rf.id), "mime_type": rf.mime_type},
        )
        _enqueue_parse(str(rf.id))

    responses = [ResumeFileResponse.model_validate(rf) for rf in uploaded]
    return UploadResponse(uploaded=responses, count=len(responses))


@router.get(
    "/resumes/{resume_id}",
    response_model=ResumeFileResponse,
    summary="Get a resume file (includes parsing status)",
    responses={
        200: {"description": "Resume file details and current parsing status."},
        404: {"description": "Resume file not found."},
    },
)
async def get_resume(
    resume_id: uuid.UUID,
    service: ResumeServiceDep,
    current_user: CurrentUser,
) -> ResumeFileResponse:
    rf = await service.get_by_id(resume_id, current_user)
    return ResumeFileResponse.model_validate(rf)


@router.get(
    "/campaigns/{campaign_id}/resumes",
    response_model=list[ResumeFileResponse],
    summary="List resume files for a campaign",
    responses={
        200: {"description": "List of resume files."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def list_resumes(
    campaign_id: uuid.UUID,
    service: ResumeServiceDep,
    current_user: CurrentUser,
) -> list[ResumeFileResponse]:
    files = await service.list_by_campaign(campaign_id, current_user)
    return [ResumeFileResponse.model_validate(rf) for rf in files]


@router.delete(
    "/resumes/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a resume file",
    responses={
        204: {"description": "Resume file deleted (soft)."},
        403: {"description": "Insufficient role or not the uploader."},
        404: {"description": "Resume file not found."},
    },
)
async def delete_resume(
    resume_id: uuid.UUID,
    service: ResumeServiceDep,
    current_user: WriteUser,
) -> None:
    await service.delete(resume_id, current_user)

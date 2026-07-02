import logging
import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import Response

from app.api.deps import CurrentUser, DBSession, RequireRoles
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.job_description import JobDescriptionRepository
from app.schemas.job_description import JobDescriptionCreate, JobDescriptionResponse
from app.services.job_description import JobDescriptionService
from app.storage.base import StorageBackend as StorageBackendType
from app.storage.factory import get_storage_backend

logger = logging.getLogger(__name__)

router = APIRouter()

_require_write_role = RequireRoles(UserRole.RECRUITER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
WriteUser = Annotated[User, Depends(_require_write_role)]
StorageDep = Annotated[StorageBackendType, Depends(get_storage_backend)]


def get_job_description_service(db: DBSession, storage: StorageDep) -> JobDescriptionService:
    return JobDescriptionService(
        JobDescriptionRepository(db),
        CampaignRepository(db),
        storage,
    )


JobDescriptionServiceDep = Annotated[JobDescriptionService, Depends(get_job_description_service)]


def _enqueue_parse(job_description_id: str) -> None:
    """Dispatch a background parse task. Lazy import avoids Celery at module import time."""
    from app.workers.job_description_parser import parse_job_description as _task  # noqa: PLC0415

    _task.delay(job_description_id)


@router.post(
    "/campaigns/{campaign_id}/job-descriptions",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Paste a job description as text",
    responses={
        201: {"description": "Job description stored and background parsing queued."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
        422: {"description": "Job description text is empty or too long."},
    },
)
async def create_job_description(
    campaign_id: uuid.UUID,
    payload: JobDescriptionCreate,
    service: JobDescriptionServiceDep,
    current_user: WriteUser,
) -> JobDescriptionResponse:
    jd = await service.create_from_text(campaign_id, payload.text, current_user)
    logger.info("Dispatching parse task", extra={"job_description_id": str(jd.id)})
    _enqueue_parse(str(jd.id))
    return JobDescriptionResponse.model_validate(jd)


@router.post(
    "/campaigns/{campaign_id}/job-descriptions/upload",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a job description file (PDF or DOCX)",
    responses={
        201: {"description": "Job description stored and background parsing queued."},
        403: {"description": "Insufficient role (CANDIDATE not permitted)."},
        404: {"description": "Campaign not found or belongs to a different organization."},
        422: {"description": "Unsupported file type, file too large, or unreadable file."},
    },
)
async def upload_job_description(
    campaign_id: uuid.UUID,
    file: UploadFile,
    service: JobDescriptionServiceDep,
    current_user: WriteUser,
) -> JobDescriptionResponse:
    jd = await service.create_from_upload(campaign_id, file, current_user)
    logger.info("Dispatching parse task", extra={"job_description_id": str(jd.id)})
    _enqueue_parse(str(jd.id))
    return JobDescriptionResponse.model_validate(jd)


@router.get(
    "/job-descriptions/{job_description_id}",
    response_model=JobDescriptionResponse,
    summary="Get a job description (includes parsing status)",
    responses={
        200: {"description": "Job description details and current parsing status."},
        404: {"description": "Job description not found."},
    },
)
async def get_job_description(
    job_description_id: uuid.UUID,
    service: JobDescriptionServiceDep,
    current_user: CurrentUser,
) -> JobDescriptionResponse:
    jd = await service.get_by_id(job_description_id, current_user)
    return JobDescriptionResponse.model_validate(jd)


@router.get(
    "/job-descriptions/{job_description_id}/download",
    summary="Download the originally uploaded job description file",
    responses={
        200: {"description": "The raw file bytes, with the original filename."},
        404: {
            "description": (
                "Job description not found, or it was pasted as text and has no source file."
            )
        },
    },
)
async def download_job_description(
    job_description_id: uuid.UUID,
    service: JobDescriptionServiceDep,
    current_user: CurrentUser,
) -> Response:
    data, mime_type, filename = await service.get_file(job_description_id, current_user)
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/campaigns/{campaign_id}/job-descriptions",
    response_model=list[JobDescriptionResponse],
    summary="List job descriptions for a campaign",
    responses={
        200: {"description": "List of job descriptions."},
        404: {"description": "Campaign not found or belongs to a different organization."},
    },
)
async def list_job_descriptions(
    campaign_id: uuid.UUID,
    service: JobDescriptionServiceDep,
    current_user: CurrentUser,
) -> list[JobDescriptionResponse]:
    job_descriptions = await service.list_by_campaign(campaign_id, current_user)
    return [JobDescriptionResponse.model_validate(jd) for jd in job_descriptions]


@router.delete(
    "/job-descriptions/{job_description_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a job description",
    responses={
        204: {"description": "Job description deleted (soft)."},
        403: {"description": "Insufficient role or not the creator."},
        404: {"description": "Job description not found."},
    },
)
async def delete_job_description(
    job_description_id: uuid.UUID,
    service: JobDescriptionServiceDep,
    current_user: WriteUser,
) -> None:
    await service.delete(job_description_id, current_user)

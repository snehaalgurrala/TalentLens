import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.job_description import JobDescription
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.job_description import JobDescriptionRepository
from app.services.resume_extraction import (
    ExtractionError,
    extract_text_from_docx_bytes,
    extract_text_from_pdf_bytes,
)
from app.storage.base import StorageBackend

_UPLOAD_EXTENSIONS = {".pdf", ".docx"}
_MAX_TEXT_LENGTH = 200_000
_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class JobDescriptionService:
    def __init__(
        self,
        repo: JobDescriptionRepository,
        campaign_repo: CampaignRepository,
        storage: StorageBackend,
    ) -> None:
        self.repo = repo
        self.campaign_repo = campaign_repo
        self.storage = storage

    # ── Internal guards ───────────────────────────────────────────────────────

    async def _require_campaign(self, campaign_id: uuid.UUID, user: User):
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage job descriptions.",
            )
        campaign = await self.campaign_repo.get_by_id(campaign_id, user.org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return campaign

    def _assert_can_write(self, job_description: JobDescription, user: User) -> None:
        if user.role in {UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN}:
            return
        if job_description.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this job description.",
            )

    def _validate_text(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Job description text must not be empty.",
            )
        if len(cleaned) > _MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Job description text exceeds the {_MAX_TEXT_LENGTH} character limit.",
            )
        return cleaned

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_from_text(
        self, campaign_id: uuid.UUID, text: str, user: User
    ) -> JobDescription:
        await self._require_campaign(campaign_id, user)
        cleaned = self._validate_text(text)
        return await self.repo.create(
            campaign_id=campaign_id,
            created_by=user.id,
            raw_text=cleaned,
        )

    async def create_from_upload(
        self, campaign_id: uuid.UUID, file: UploadFile, user: User
    ) -> JobDescription:
        await self._require_campaign(campaign_id, user)

        filename = file.filename or "upload"
        ext = Path(filename).suffix.lower()
        if ext not in _UPLOAD_EXTENSIONS:
            allowed = ", ".join(sorted(e.lstrip(".").upper() for e in _UPLOAD_EXTENSIONS))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"File '{filename}' has unsupported extension '{ext or '(none)'}'. "
                    f"Allowed: {allowed}."
                ),
            )

        data = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"File '{filename}' is {len(data) / (1024 * 1024):.1f} MB, "
                    f"which exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
                ),
            )

        try:
            if ext == ".pdf":
                text = await extract_text_from_pdf_bytes(data, filename)
            else:
                text = await extract_text_from_docx_bytes(data, filename)
        except ExtractionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        cleaned = self._validate_text(text)

        stored_name = f"{uuid.uuid4()}{ext}"
        relative_path = f"job-descriptions/{campaign_id}/{stored_name}"
        await self.storage.save(relative_path, data)

        return await self.repo.create(
            campaign_id=campaign_id,
            created_by=user.id,
            original_filename=filename,
            storage_path=relative_path,
            mime_type=_MIME_BY_EXT[ext],
            file_size=len(data),
            raw_text=cleaned,
        )

    async def get_by_id(self, job_description_id: uuid.UUID, user: User) -> JobDescription:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view job descriptions.",
            )
        jd = await self.repo.get_by_id(job_description_id)
        if jd is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found.",
            )
        campaign = await self.campaign_repo.get_by_id(jd.campaign_id, user.org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found.",
            )
        return jd

    async def list_by_campaign(
        self, campaign_id: uuid.UUID, user: User
    ) -> list[JobDescription]:
        await self._require_campaign(campaign_id, user)
        return await self.repo.list_by_campaign(campaign_id)

    async def get_file(self, job_description_id: uuid.UUID, user: User) -> tuple[bytes, str, str]:
        """Returns (raw file bytes, mime type, filename) for the originally
        uploaded JD file. Only available for JDs created via file upload."""
        jd = await self.get_by_id(job_description_id, user)
        if jd.storage_path is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This job description was pasted as text and has no source file to download.",
            )
        data = await self.storage.load(jd.storage_path)
        filename = jd.original_filename or "job-description"
        mime_type = jd.mime_type or "application/octet-stream"
        return data, mime_type, filename

    async def delete(self, job_description_id: uuid.UUID, user: User) -> None:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage job descriptions.",
            )
        jd = await self.repo.get_by_id(job_description_id)
        if jd is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found.",
            )
        campaign = await self.campaign_repo.get_by_id(jd.campaign_id, user.org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found.",
            )
        self._assert_can_write(jd, user)
        await self.repo.soft_delete(jd)

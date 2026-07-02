import io
import uuid
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.resume_file import ResumeFile, UploadStatus
from app.models.user import User, UserRole
from app.repositories.campaign import CampaignRepository
from app.repositories.resume_file import ResumeFileRepository
from app.services.resume_extraction import ZipSafetyError, validate_zip_safety
from app.storage.base import StorageBackend

# Extensions accepted directly in an upload
_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".zip"}
# Extensions accepted inside a ZIP archive
_ARCHIVE_EXTENSIONS = {".pdf", ".docx"}

_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ResumeFileService:
    def __init__(
        self,
        repo: ResumeFileRepository,
        campaign_repo: CampaignRepository,
        storage: StorageBackend,
    ) -> None:
        self.repo = repo
        self.campaign_repo = campaign_repo
        self.storage = storage

    # ── Internal guards ───────────────────────────────────────────────────────

    def _max_bytes(self) -> int:
        return settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    async def _require_campaign(self, campaign_id: uuid.UUID, user: User):
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage resumes.",
            )
        campaign = await self.campaign_repo.get_by_id(campaign_id, user.org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found.",
            )
        return campaign

    def _assert_can_write(self, resume_file: ResumeFile, user: User) -> None:
        if user.role in {UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN}:
            return
        if resume_file.uploaded_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this file.",
            )

    # ── File validation helpers ───────────────────────────────────────────────

    def _validate_extension(self, filename: str, allowed: set[str]) -> str:
        ext = Path(filename).suffix.lower()
        if ext not in allowed:
            allowed_str = ", ".join(sorted(e.lstrip(".").upper() for e in allowed))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"File '{filename}' has unsupported extension '{ext or '(none)'}'. "
                    f"Allowed: {allowed_str}."
                ),
            )
        return ext

    def _validate_size(self, filename: str, data: bytes) -> None:
        max_bytes = self._max_bytes()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"File '{filename}' is {len(data) / (1024 * 1024):.1f} MB, "
                    f"which exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
                ),
            )

    def _extract_zip(
        self, zip_filename: str, data: bytes
    ) -> list[tuple[str, bytes, str]]:
        """Extract PDF/DOCX entries from a ZIP; raises 422 on any violation."""
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'{zip_filename}' is not a valid ZIP file.",
            )

        try:
            validate_zip_safety(zf)
        except ZipSafetyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'{zip_filename}': {exc}",
            )

        results: list[tuple[str, bytes, str]] = []
        with zf:
            for entry in zf.infolist():
                if entry.is_dir():
                    continue
                # Use only the basename to avoid path-traversal issues
                name = Path(entry.filename).name
                ext = self._validate_extension(
                    f"{zip_filename}/{entry.filename}", _ARCHIVE_EXTENSIONS
                )
                content = zf.read(entry.filename)
                self._validate_size(f"{zip_filename}/{name}", content)
                results.append((name, content, _MIME_BY_EXT[ext]))

        if not results:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"ZIP '{zip_filename}' contains no supported PDF or DOCX files.",
            )
        return results

    # ── Public API ────────────────────────────────────────────────────────────

    async def upload(
        self,
        campaign_id: uuid.UUID,
        files: list[UploadFile],
        user: User,
    ) -> list[ResumeFile]:
        await self._require_campaign(campaign_id, user)

        # Phase 1: read and validate every file before writing anything
        to_save: list[tuple[str, bytes, str]] = []
        for upload in files:
            filename = upload.filename or "upload"
            ext = self._validate_extension(filename, _UPLOAD_EXTENSIONS)
            data = await upload.read()
            self._validate_size(filename, data)

            if ext == ".zip":
                to_save.extend(self._extract_zip(filename, data))
            else:
                to_save.append((filename, data, _MIME_BY_EXT[ext]))

        # Phase 2: persist all validated files
        created: list[ResumeFile] = []
        for original_name, data, mime_type in to_save:
            ext = Path(original_name).suffix.lower()
            stored_name = f"{uuid.uuid4()}{ext}"
            relative_path = f"{campaign_id}/{stored_name}"
            await self.storage.save(relative_path, data)
            rf = await self.repo.create(
                campaign_id=campaign_id,
                original_filename=original_name,
                stored_filename=stored_name,
                mime_type=mime_type,
                file_size=len(data),
                storage_path=relative_path,
                upload_status=UploadStatus.UPLOADED,
                uploaded_by=user.id,
            )
            created.append(rf)

        return created

    async def get_by_id(self, resume_id: uuid.UUID, user: User) -> ResumeFile:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to view resumes.",
            )
        rf = await self.repo.get_by_id(resume_id)
        if rf is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume file not found.",
            )
        # Verify the file belongs to the user's organization via its campaign
        campaign = await self.campaign_repo.get_by_id(rf.campaign_id, user.org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume file not found.",
            )
        return rf

    async def list_by_campaign(
        self, campaign_id: uuid.UUID, user: User
    ) -> list[ResumeFile]:
        await self._require_campaign(campaign_id, user)
        return await self.repo.list_by_campaign(campaign_id)

    async def delete(self, resume_id: uuid.UUID, user: User) -> None:
        if user.org_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You must belong to an organization to manage resumes.",
            )
        rf = await self.repo.get_by_id(resume_id)
        if rf is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume file not found.",
            )
        # Verify the file's campaign belongs to the user's org
        campaign = await self.campaign_repo.get_by_id(rf.campaign_id, user.org_id)
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume file not found.",
            )
        self._assert_can_write(rf, user)
        await self.repo.soft_delete(rf)

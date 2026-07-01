from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.resume_file import UploadStatus


class ResumeFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    storage_path: str
    upload_status: UploadStatus
    uploaded_by: UUID | None
    candidate_id: UUID | None
    error_message: str | None
    is_deleted: bool
    uploaded_at: datetime


class UploadResponse(BaseModel):
    uploaded: list[ResumeFileResponse]
    count: int

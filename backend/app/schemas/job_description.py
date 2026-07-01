from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.embedding import EmbeddingStatus
from app.models.job_description import ParsingStatus


class JobDescriptionCreate(BaseModel):
    text: str = Field(..., min_length=1)


class JobDescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    created_by: UUID | None
    original_filename: str | None
    raw_text: str
    structured_json: dict[str, Any] | None
    parser_version: str | None
    parsed_at: datetime | None
    parsing_status: ParsingStatus
    parsing_error: str | None
    embedding_status: EmbeddingStatus
    embedding_model: str | None
    embedding_generated_at: datetime | None
    embedding_dimension: int | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

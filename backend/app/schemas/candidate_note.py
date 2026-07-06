from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserSummaryResponse


class CandidateNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_file_id: UUID
    author: UserSummaryResponse | None
    body: str
    created_at: datetime
    updated_at: datetime
    can_edit: bool = False
    is_pinned: bool = False
    mentioned_user_ids: list[UUID] = Field(default_factory=list)


class CandidateNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    mentioned_user_ids: list[UUID] = Field(default_factory=list)


class CandidateNoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    mentioned_user_ids: list[UUID] = Field(default_factory=list)


class CandidateNotePinUpdate(BaseModel):
    is_pinned: bool

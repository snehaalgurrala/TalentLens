from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    org_id: UUID | None
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    """Email is intentionally not editable here — changing it needs its own
    re-verification flow, out of scope for this build."""

    full_name: str | None = Field(None, min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserSummaryResponse(BaseModel):
    """Minimal user shape for embedding in other responses (e.g. a campaign's
    hiring manager/recruiter) or populating assignment dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    role: UserRole

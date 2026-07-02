from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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


class UserSummaryResponse(BaseModel):
    """Minimal user shape for embedding in other responses (e.g. a campaign's
    hiring manager/recruiter) or populating assignment dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    role: UserRole

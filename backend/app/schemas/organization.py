from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.organization_invitation import InvitationStatus
from app.schemas.auth import TokenResponse
from app.schemas.user import UserResponse

_SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class OrganizationBootstrapRequest(BaseModel):
    """Creates a brand-new organization plus its first ORG_ADMIN user."""

    org_name: str = Field(min_length=1, max_length=255)
    org_slug: str = Field(min_length=1, max_length=100, pattern=_SLUG_PATTERN)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str = Field(min_length=1, max_length=255)


class OrganizationBootstrapResponse(BaseModel):
    organization: OrganizationResponse
    admin: UserResponse
    tokens: TokenResponse


class InvitationCreate(BaseModel):
    email: EmailStr


class InvitationResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    status: InvitationStatus
    expires_at: datetime
    # Raw token — only ever present in the response to the creation call.
    token: str

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
    logo_url: str | None = None
    industry: str | None = None
    website: str | None = None
    company_email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    timezone: str
    description: str | None = None
    created_at: datetime


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    company_email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    timezone: str | None = Field(None, max_length=50)
    description: str | None = None


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

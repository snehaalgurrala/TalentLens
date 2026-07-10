from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.platform_email_config import EmailTestResult


class PlatformEmailConfigUpdate(BaseModel):
    smtp_host: str | None = Field(None, max_length=255)
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_username: str | None = Field(None, max_length=255)
    smtp_password: str | None = Field(None, max_length=255)
    smtp_from_email: EmailStr | None = None
    smtp_from_name: str | None = Field(None, max_length=255)
    smtp_tls: bool | None = None
    smtp_ssl: bool | None = None


class PlatformEmailConfigResponse(BaseModel):
    """smtp_password is intentionally never returned — see has_password."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_tls: bool
    smtp_ssl: bool
    is_configured: bool
    has_password: bool
    last_test_at: datetime | None
    last_test_status: EmailTestResult | None
    last_test_error: str | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime


class SendTestEmailRequest(BaseModel):
    to_email: EmailStr


class SendTestEmailResponse(BaseModel):
    success: bool
    error: str | None = None

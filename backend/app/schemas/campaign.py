from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.campaign import CampaignStatus


class CampaignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    status: CampaignStatus = CampaignStatus.DRAFT


class CampaignUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: CampaignStatus | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    created_by: UUID | None
    title: str
    description: str | None
    status: CampaignStatus
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

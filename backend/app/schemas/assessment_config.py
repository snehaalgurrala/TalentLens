from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssessmentConfigUpdate(BaseModel):
    read_aloud_reference_sentence: str | None = Field(None, min_length=1, max_length=2000)
    listen_repeat_reference_sentence: str | None = Field(None, min_length=1, max_length=2000)


class AssessmentConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    read_aloud_reference_sentence: str
    listen_repeat_reference_sentence: str
    created_at: datetime
    updated_at: datetime

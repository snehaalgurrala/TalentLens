from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.candidate_activity import ActivityEventType
from app.schemas.user import UserSummaryResponse


class CandidateActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: ActivityEventType
    actor: UserSummaryResponse | None
    event_metadata: dict[str, Any] | None
    created_at: datetime

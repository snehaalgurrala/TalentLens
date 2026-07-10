from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_label: str | None
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    last_seen_at: datetime
    # Computed by the service by comparing to the requesting session — not a
    # DB column.
    is_current: bool = False

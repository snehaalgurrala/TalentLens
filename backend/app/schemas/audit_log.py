from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID | None
    actor_id: UUID | None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: UUID | None
    event_metadata: dict | None
    ip_address: str | None
    result: str
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int

import uuid
from datetime import datetime
from typing import Any

from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogEntry, AuditLogListResponse


class AuditLogService:
    """Thin, extensible instrumentation point. See app/services/audit_log.py
    callers across the codebase for the currently-wired call sites — this is
    a documented, growing subset, not exhaustive coverage of every mutating
    action in the app."""

    def __init__(self, repo: AuditLogRepository) -> None:
        self.repo = repo

    async def record(
        self,
        *,
        org_id: uuid.UUID | None,
        actor_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        result: str = "success",
    ) -> None:
        await self.repo.create(
            org_id=org_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            event_metadata=metadata,
            ip_address=ip_address,
            result=result,
        )

    async def list(
        self,
        user: User,
        *,
        org_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditLogListResponse:
        # SUPER_ADMIN may pass an explicit org_id filter to cross-org view;
        # otherwise (like ORG_ADMIN) they're scoped to their own org.
        scoped_org_id = org_id
        if user.role != UserRole.SUPER_ADMIN or scoped_org_id is None:
            scoped_org_id = org_id if org_id is not None else user.org_id

        rows, total = await self.repo.list_paginated(
            org_id=scoped_org_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        items = [
            AuditLogEntry(
                id=r.id,
                org_id=r.org_id,
                actor_id=r.actor_id,
                # Not eager-loaded by list_paginated (lazy="raise" on
                # AuditLog.actor) — the frontend resolves actor_id to a name
                # from its own org-members list rather than paying for a
                # join here on every page of the audit log.
                actor_name=None,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                event_metadata=r.event_metadata,
                ip_address=r.ip_address,
                result=r.result,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return AuditLogListResponse(items=items, total=total, limit=limit, offset=offset)

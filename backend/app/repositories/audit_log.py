import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: Any) -> AuditLog:
        row = AuditLog(**kwargs)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_paginated(
        self,
        *,
        org_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)

        filters = []
        if org_id is not None:
            filters.append(AuditLog.org_id == org_id)
        if actor_id is not None:
            filters.append(AuditLog.actor_id == actor_id)
        if action is not None:
            filters.append(AuditLog.action == action)
        if entity_type is not None:
            filters.append(AuditLog.entity_type == entity_type)
        if date_from is not None:
            filters.append(AuditLog.created_at >= date_from)
        if date_to is not None:
            filters.append(AuditLog.created_at <= date_to)

        for f in filters:
            stmt = stmt.where(f)
            count_stmt = count_stmt.where(f)

        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        total = (await self.session.execute(count_stmt)).scalar_one()
        return list(result.scalars().all()), total

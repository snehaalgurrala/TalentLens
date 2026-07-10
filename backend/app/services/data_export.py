import csv
import io
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_session import AssessmentSession
from app.models.audit_log import AuditLog
from app.models.candidate import Candidate


class _CsvBuffer:
    """Minimal file-like adapter so csv.writer can target an in-memory
    buffer we flush and clear after each row — keeps memory flat for large
    exports instead of building the whole CSV in memory."""

    def __init__(self) -> None:
        self._buffer = io.StringIO()

    def write(self, row: str) -> None:
        self._buffer.write(row)

    def read(self) -> str:
        data = self._buffer.getvalue()
        self._buffer.seek(0)
        self._buffer.truncate(0)
        return data


class DataExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export_candidates_csv(self, org_id: uuid.UUID) -> AsyncIterator[str]:
        buffer = _CsvBuffer()
        writer = csv.writer(buffer)
        header = [
            "id", "first_name", "last_name", "email", "phone", "location",
            "years_of_experience", "current_company", "current_role", "created_at",
        ]
        writer.writerow(header)
        yield buffer.read()

        result = await self.session.stream(
            select(Candidate).where(Candidate.organization_id == org_id).order_by(Candidate.created_at)
        )
        async for (candidate,) in result:
            writer.writerow(
                [
                    str(candidate.id), candidate.first_name, candidate.last_name,
                    candidate.email or "", candidate.phone or "", candidate.location or "",
                    candidate.years_of_experience or "", candidate.current_company or "",
                    candidate.current_role or "", candidate.created_at.isoformat(),
                ]
            )
            yield buffer.read()

    async def export_assessments_csv(self, org_id: uuid.UUID) -> AsyncIterator[str]:
        buffer = _CsvBuffer()
        writer = csv.writer(buffer)
        header = [
            "id", "campaign_id", "candidate_id", "status", "current_section",
            "started_at", "completed_at",
        ]
        writer.writerow(header)
        yield buffer.read()

        result = await self.session.stream(
            select(AssessmentSession)
            .where(AssessmentSession.org_id == org_id)
            .order_by(AssessmentSession.started_at)
        )
        async for (session_row,) in result:
            writer.writerow(
                [
                    str(session_row.id), str(session_row.campaign_id), str(session_row.candidate_id),
                    session_row.status.value, session_row.current_section.value,
                    session_row.started_at.isoformat(),
                    session_row.completed_at.isoformat() if session_row.completed_at else "",
                ]
            )
            yield buffer.read()

    async def export_audit_log_csv(self, org_id: uuid.UUID) -> AsyncIterator[str]:
        buffer = _CsvBuffer()
        writer = csv.writer(buffer)
        header = ["id", "actor_id", "action", "entity_type", "entity_id", "result", "created_at"]
        writer.writerow(header)
        yield buffer.read()

        result = await self.session.stream(
            select(AuditLog).where(AuditLog.org_id == org_id).order_by(AuditLog.created_at)
        )
        async for (row,) in result:
            writer.writerow(
                [
                    str(row.id), str(row.actor_id) if row.actor_id else "", row.action,
                    row.entity_type, str(row.entity_id) if row.entity_id else "",
                    row.result, row.created_at.isoformat(),
                ]
            )
            yield buffer.read()

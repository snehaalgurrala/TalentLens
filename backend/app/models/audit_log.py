import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class AuditLog(Base):
    """General-purpose admin/org audit trail. Distinct from CandidateActivity
    (which is resume_file-scoped, candidate-pipeline-specific). `action` is a
    free-form dotted string (e.g. "organization.updated") rather than an enum
    since the action set grows continuously as more call sites are
    instrumented — see AuditLogService.record for the (currently partial,
    documented as such) list of call sites that write here."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Python attribute renamed from the "metadata" column — SQLAlchemy's
    # DeclarativeBase reserves the bare `metadata` name for the class's
    # MetaData object.
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[str] = mapped_column(String(10), nullable=False, default="success", server_default="success")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    organization: Mapped["Organization | None"] = relationship("Organization", lazy="raise")
    actor: Mapped["User | None"] = relationship("User", lazy="raise")

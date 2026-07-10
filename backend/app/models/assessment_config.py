import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class AssessmentConfig(Base):
    """Org-scoped singleton holding the Read Aloud / Listen & Repeat reference
    sentences. Created lazily (get-or-create) on first access, seeded from
    Settings.READ_ALOUD_REFERENCE_SENTENCE / LISTEN_REPEAT_REFERENCE_SENTENCE."""

    __tablename__ = "assessment_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    read_aloud_reference_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    listen_repeat_reference_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class RecruitmentSettings(Base):
    """Org-scoped singleton: resume ranking policy fields that aren't part of
    ScoringRule's weighted-average contract (see [[ScoringRule]] for the
    ranking weights themselves)."""

    __tablename__ = "recruitment_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    default_resume_score_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=60.0, server_default="60.0"
    )
    enable_explainable_ai: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    max_resume_upload_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=20, server_default="20"
    )
    max_resume_size_mb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default="10"
    )
    supported_resume_formats: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: ["pdf", "doc", "docx"],
        server_default=text("'[\"pdf\", \"doc\", \"docx\"]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")

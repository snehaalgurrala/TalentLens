import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.organization import Organization
    from app.models.user import User


class ScoringRule(Base):
    """
    A weighted-average scoring configuration. `campaign_id IS NULL` means
    this row is an organization's default; a non-null `campaign_id` means
    it's an override scoped to that one campaign. At most one default row
    exists per org, and at most one override row exists per campaign (see
    __table_args__ / the unique constraint on campaign_id).
    """

    __tablename__ = "scoring_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    semantic_weight: Mapped[float] = mapped_column(Float, nullable=False)
    skills_weight: Mapped[float] = mapped_column(Float, nullable=False)
    experience_weight: Mapped[float] = mapped_column(Float, nullable=False)
    education_weight: Mapped[float] = mapped_column(Float, nullable=False)
    project_weight: Mapped[float] = mapped_column(Float, nullable=False)
    certification_weight: Mapped[float] = mapped_column(Float, nullable=False)

    # Fraction added to the weighted average when the candidate's current
    # company is in preferred_companies. Capped at 0.05 (5%) — enforced at
    # the schema layer and re-checked in ScoringRuleService.compute_final_score.
    preferred_company_bonus: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )
    preferred_companies: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship("Organization", lazy="raise")
    campaign: Mapped["Campaign | None"] = relationship("Campaign", lazy="raise")
    creator: Mapped["User | None"] = relationship("User", lazy="raise")

    __table_args__ = (
        Index(
            "ux_scoring_rules_org_default",
            "org_id",
            unique=True,
            postgresql_where=text("campaign_id IS NULL"),
        ),
    )

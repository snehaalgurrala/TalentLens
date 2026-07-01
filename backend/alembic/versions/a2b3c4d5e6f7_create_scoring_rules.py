"""Create scoring_rules table

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scoring_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # NULL = organization default. Set = override scoped to one campaign.
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("semantic_weight", sa.Float, nullable=False),
        sa.Column("skills_weight", sa.Float, nullable=False),
        sa.Column("experience_weight", sa.Float, nullable=False),
        sa.Column("education_weight", sa.Float, nullable=False),
        sa.Column("project_weight", sa.Float, nullable=False),
        sa.Column("certification_weight", sa.Float, nullable=False),
        sa.Column(
            "preferred_company_bonus", sa.Float, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "preferred_companies",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_scoring_rules_org_id", "scoring_rules", ["org_id"])
    # At most one organization-default row (campaign_id IS NULL) per org.
    # Campaign overrides are already uniquely constrained via campaign_id's
    # own unique constraint above.
    op.create_index(
        "ux_scoring_rules_org_default",
        "scoring_rules",
        ["org_id"],
        unique=True,
        postgresql_where=sa.text("campaign_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("scoring_rules")

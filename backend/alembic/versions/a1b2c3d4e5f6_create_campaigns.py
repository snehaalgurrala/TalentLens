"""Create campaigns table

Revision ID: a1b2c3d4e5f6
Revises: f1e2d3c4b5a6
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. PostgreSQL ENUM type ───────────────────────────────────────────────
    op.execute(
        "CREATE TYPE campaignstatus AS ENUM "
        "('DRAFT', 'ACTIVE', 'PAUSED', 'CLOSED', 'ARCHIVED')"
    )

    # ── 2. campaigns ──────────────────────────────────────────────────────────
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT", "ACTIVE", "PAUSED", "CLOSED", "ARCHIVED",
                name="campaignstatus",
                create_type=False,  # already created above
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_campaigns_org_id", "campaigns", ["org_id"])
    op.create_index("ix_campaigns_created_by", "campaigns", ["created_by"])
    op.create_index("ix_campaigns_is_deleted", "campaigns", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("campaigns")
    op.execute("DROP TYPE IF EXISTS campaignstatus")

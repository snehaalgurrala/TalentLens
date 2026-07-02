"""Create job_descriptions table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-01 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. PostgreSQL ENUM types ─────────────────────────────────────────────
    op.execute(
        "CREATE TYPE parsingstatus AS ENUM "
        "('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')"
    )
    op.execute(
        "CREATE TYPE embeddingstatus AS ENUM "
        "('PENDING', 'GENERATING', 'READY', 'FAILED')"
    )

    # ── 2. job_descriptions ───────────────────────────────────────────────────
    op.create_table(
        "job_descriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("structured_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("parser_version", sa.String(50), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "parsing_status",
            postgresql.ENUM(
                "PENDING", "PROCESSING", "COMPLETED", "FAILED",
                name="parsingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("parsing_error", sa.Text, nullable=True),
        sa.Column(
            "embedding_status",
            postgresql.ENUM(
                "PENDING", "GENERATING", "READY", "FAILED",
                name="embeddingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("embedding_generated_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_job_descriptions_campaign_id", "job_descriptions", ["campaign_id"])
    op.create_index("ix_job_descriptions_created_by", "job_descriptions", ["created_by"])
    op.create_index("ix_job_descriptions_is_deleted", "job_descriptions", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_job_descriptions_is_deleted", table_name="job_descriptions")
    op.drop_index("ix_job_descriptions_created_by", table_name="job_descriptions")
    op.drop_index("ix_job_descriptions_campaign_id", table_name="job_descriptions")
    op.drop_table("job_descriptions")
    op.execute("DROP TYPE IF EXISTS embeddingstatus")
    op.execute("DROP TYPE IF EXISTS parsingstatus")

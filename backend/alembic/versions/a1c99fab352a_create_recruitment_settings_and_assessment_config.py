"""Create recruitment_settings and assessment_configs

Revision ID: a1c99fab352a
Revises: a1498e50de0f
Create Date: 2026-07-09 00:00:01.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "a1c99fab352a"
down_revision: str | None = "a1498e50de0f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recruitment_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "default_resume_score_threshold",
            sa.Float,
            nullable=False,
            server_default=sa.text("60.0"),
        ),
        sa.Column(
            "enable_explainable_ai", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "max_resume_upload_count", sa.Integer, nullable=False, server_default=sa.text("20")
        ),
        sa.Column(
            "max_resume_size_mb", sa.Integer, nullable=False, server_default=sa.text("10")
        ),
        sa.Column(
            "supported_resume_formats",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[\"pdf\", \"doc\", \"docx\"]'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )

    op.create_table(
        "assessment_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("read_aloud_reference_sentence", sa.Text(), nullable=False),
        sa.Column("listen_repeat_reference_sentence", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )


def downgrade() -> None:
    op.drop_table("assessment_configs")
    op.drop_table("recruitment_settings")

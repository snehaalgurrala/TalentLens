"""Create resume_files table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. PostgreSQL ENUM type ───────────────────────────────────────────────
    op.execute(
        "CREATE TYPE uploadstatus AS ENUM "
        "('PENDING', 'UPLOADED', 'PROCESSING', 'PARSED', 'FAILED')"
    )

    # ── 2. resume_files ───────────────────────────────────────────────────────
    op.create_table(
        "resume_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column(
            "upload_status",
            postgresql.ENUM(
                "PENDING", "UPLOADED", "PROCESSING", "PARSED", "FAILED",
                name="uploadstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="UPLOADED",
        ),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_resume_files_campaign_id", "resume_files", ["campaign_id"])
    op.create_index("ix_resume_files_uploaded_by", "resume_files", ["uploaded_by"])
    op.create_index("ix_resume_files_is_deleted", "resume_files", ["is_deleted"])


def downgrade() -> None:
    op.drop_table("resume_files")
    op.execute("DROP TYPE IF EXISTS uploadstatus")

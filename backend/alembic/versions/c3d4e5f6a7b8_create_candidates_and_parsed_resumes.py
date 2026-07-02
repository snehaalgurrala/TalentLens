"""Create candidates and parsed_resumes tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-30 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. candidates ─────────────────────────────────────────────────────────
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("linkedin_url", sa.String(1024), nullable=True),
        sa.Column("github_url", sa.String(1024), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("years_of_experience", sa.Float, nullable=True),
        sa.Column("current_company", sa.String(255), nullable=True),
        sa.Column("current_role", sa.String(255), nullable=True),
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
    op.create_index("ix_candidates_organization_id", "candidates", ["organization_id"])
    op.create_index("ix_candidates_email", "candidates", ["email"])

    # ── 2. parsed_resumes ─────────────────────────────────────────────────────
    op.create_table(
        "parsed_resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resume_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resume_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("structured_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parser_version", sa.String(50), nullable=False),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_parsed_resumes_resume_file_id", "parsed_resumes", ["resume_file_id"])
    op.create_index("ix_parsed_resumes_candidate_id", "parsed_resumes", ["candidate_id"])


def downgrade() -> None:
    op.drop_table("parsed_resumes")
    op.drop_table("candidates")

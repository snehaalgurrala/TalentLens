"""Create assessment_analyses

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-07 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_analysis_type = sa.Enum("READ_ALOUD", name="analysistype")
_analysis_status = sa.Enum("PENDING", "COMPLETED", "FAILED", name="analysisstatus")


def upgrade() -> None:
    # Do NOT also call _analysis_type.create() / _analysis_status.create() here:
    # with asyncpg, create_table's own column DDL already emits CREATE TYPE for
    # these enums, so a prior explicit .create() call causes a DuplicateObjectError.
    op.create_table(
        "assessment_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_type", _analysis_type, nullable=False, server_default="READ_ALOUD"),
        sa.Column("status", _analysis_status, nullable=False, server_default="PENDING"),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("word_accuracy", sa.Float(), nullable=True),
        sa.Column("correct_words", sa.Integer(), nullable=True),
        sa.Column("missing_words", sa.Integer(), nullable=True),
        sa.Column("extra_words", sa.Integer(), nullable=True),
        sa.Column("substituted_words", sa.Integer(), nullable=True),
        sa.Column("total_words", sa.Integer(), nullable=True),
        sa.Column("reading_speed_wpm", sa.Float(), nullable=True),
        sa.Column("completion_percentage", sa.Float(), nullable=True),
        sa.Column("analysis_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transcript_id", name="uq_assessment_analyses_transcript_id"),
    )
    op.create_index(
        op.f("ix_assessment_analyses_organization_id"),
        "assessment_analyses",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_assessment_analyses_transcript_id"),
        "assessment_analyses",
        ["transcript_id"],
    )
    op.create_foreign_key(
        "fk_assessment_analyses_organization_id_organizations",
        "assessment_analyses",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_assessment_analyses_transcript_id_assessment_transcripts",
        "assessment_analyses",
        "assessment_transcripts",
        ["transcript_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_assessment_analyses_transcript_id_assessment_transcripts",
        "assessment_analyses",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_assessment_analyses_organization_id_organizations",
        "assessment_analyses",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_assessment_analyses_transcript_id"), table_name="assessment_analyses"
    )
    op.drop_index(
        op.f("ix_assessment_analyses_organization_id"), table_name="assessment_analyses"
    )
    op.drop_table("assessment_analyses")
    _analysis_status.drop(op.get_bind(), checkfirst=True)
    _analysis_type.drop(op.get_bind(), checkfirst=True)

"""Create assessment_transcripts

Revision ID: c1d2e3f4a5b6
Revises: b4c5d6e7f8a9
Create Date: 2026-07-07 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_transcript_status = sa.Enum(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="transcriptstatus"
)


def upgrade() -> None:
    # Do NOT also call _transcript_status.create() here: with asyncpg,
    # create_table's own column DDL already emits CREATE TYPE for this enum,
    # so a prior explicit .create() call causes a DuplicateObjectError.
    op.create_table(
        "assessment_transcripts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("recording_id", sa.Uuid(), nullable=False),
        sa.Column("status", _transcript_status, nullable=False, server_default="PENDING"),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("segment_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recording_id", name="uq_assessment_transcripts_recording_id"),
    )
    op.create_index(
        op.f("ix_assessment_transcripts_organization_id"),
        "assessment_transcripts",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_assessment_transcripts_recording_id"),
        "assessment_transcripts",
        ["recording_id"],
    )
    op.create_foreign_key(
        "fk_assessment_transcripts_organization_id_organizations",
        "assessment_transcripts",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_assessment_transcripts_recording_id_assessment_recordings",
        "assessment_transcripts",
        "assessment_recordings",
        ["recording_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_assessment_transcripts_recording_id_assessment_recordings",
        "assessment_transcripts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_assessment_transcripts_organization_id_organizations",
        "assessment_transcripts",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_assessment_transcripts_recording_id"), table_name="assessment_transcripts"
    )
    op.drop_index(
        op.f("ix_assessment_transcripts_organization_id"), table_name="assessment_transcripts"
    )
    op.drop_table("assessment_transcripts")
    _transcript_status.drop(op.get_bind(), checkfirst=True)

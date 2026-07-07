"""Create communication_assessments

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-07 00:00:02.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_communication_assessment_status = sa.Enum(
    "PENDING", "COMPLETED", "FAILED", name="communicationassessmentstatus"
)


def upgrade() -> None:
    # Do NOT also call _communication_assessment_status.create() here:
    # with asyncpg, create_table's own column DDL already emits CREATE TYPE
    # for this enum, so a prior explicit .create() call causes a
    # DuplicateObjectError (see d2e3f4a5b6c7_create_assessment_analyses.py).
    op.create_table(
        "communication_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", _communication_assessment_status, nullable=False, server_default="PENDING"
        ),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("reading_score", sa.Float(), nullable=True),
        sa.Column("listening_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("strengths_json", postgresql.JSONB(), nullable=True),
        sa.Column("improvements_json", postgresql.JSONB(), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_session_id", name="uq_communication_assessments_assessment_session_id"
        ),
    )
    op.create_index(
        op.f("ix_communication_assessments_organization_id"),
        "communication_assessments",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_communication_assessments_assessment_session_id"),
        "communication_assessments",
        ["assessment_session_id"],
    )
    op.create_foreign_key(
        "fk_communication_assessments_organization_id_organizations",
        "communication_assessments",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Constraint name shortened (ref table "sessions" rather than
    # "assessment_sessions") to stay under Postgres' 63-byte identifier limit.
    op.create_foreign_key(
        "fk_communication_assessments_assessment_session_id_sessions",
        "communication_assessments",
        "assessment_sessions",
        ["assessment_session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_communication_assessments_assessment_session_id_sessions",
        "communication_assessments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_communication_assessments_organization_id_organizations",
        "communication_assessments",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_communication_assessments_assessment_session_id"),
        table_name="communication_assessments",
    )
    op.drop_index(
        op.f("ix_communication_assessments_organization_id"),
        table_name="communication_assessments",
    )
    op.drop_table("communication_assessments")
    _communication_assessment_status.drop(op.get_bind(), checkfirst=True)

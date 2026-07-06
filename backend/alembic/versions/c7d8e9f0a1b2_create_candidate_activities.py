"""Create candidate_activities

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-07-06 00:00:01.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers
revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_event_type = sa.Enum(
    "RESUME_UPLOADED",
    "PARSING_STARTED",
    "PARSED",
    "PARSE_FAILED",
    "RANKED",
    "VIEWED",
    "SHORTLISTED",
    "REJECTED",
    "PIPELINE_STAGE_CHANGED",
    "RECRUITER_ASSIGNED",
    "NOTE_ADDED",
    name="activityeventtype",
)


def upgrade() -> None:
    # Do NOT also call _event_type.create(..., checkfirst=True) here: with
    # asyncpg, create_table's own column DDL already emits CREATE TYPE for
    # the enum (checkfirst=False under the hood), so a prior explicit
    # .create() call causes a DuplicateObjectError on this exact type.
    op.create_table(
        "candidate_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_file_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", _event_type, nullable=False),
        sa.Column("event_metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_activities_resume_file_id"), "candidate_activities", ["resume_file_id"]
    )
    op.create_index(op.f("ix_candidate_activities_actor_id"), "candidate_activities", ["actor_id"])
    op.create_foreign_key(
        "fk_candidate_activities_resume_file_id_resume_files",
        "candidate_activities",
        "resume_files",
        ["resume_file_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_candidate_activities_actor_id_users",
        "candidate_activities",
        "users",
        ["actor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_candidate_activities_actor_id_users", "candidate_activities", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_candidate_activities_resume_file_id_resume_files",
        "candidate_activities",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_candidate_activities_actor_id"), table_name="candidate_activities")
    op.drop_index(op.f("ix_candidate_activities_resume_file_id"), table_name="candidate_activities")
    op.drop_table("candidate_activities")
    _event_type.drop(op.get_bind(), checkfirst=True)

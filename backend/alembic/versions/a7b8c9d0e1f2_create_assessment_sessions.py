"""Create assessment_sessions, assessment_answers, assessment_recordings

Revision ID: a7b8c9d0e1f2
Revises: f3a4b5c6d7e8
Create Date: 2026-07-07 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_assessment_section = sa.Enum(
    "APTITUDE", "READ_ALOUD", "LISTEN_REPEAT", name="assessmentsection"
)
_assessment_session_status = sa.Enum(
    "IN_PROGRESS", "COMPLETED", name="assessmentsessionstatus"
)
_recording_type = sa.Enum("READ_ALOUD", "LISTEN_REPEAT", name="recordingtype")
_recording_status = sa.Enum("PENDING", "UPLOADED", "FAILED", name="recordingstatus")


def upgrade() -> None:
    # Do NOT also call these enums' .create() here: with asyncpg,
    # create_table's own column DDL already emits CREATE TYPE for each enum,
    # so a prior explicit .create() call causes a DuplicateObjectError.
    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column(
            "current_section", _assessment_section, nullable=False, server_default="APTITUDE"
        ),
        sa.Column("current_question", sa.Integer(), nullable=True),
        sa.Column(
            "status", _assessment_session_status, nullable=False, server_default="IN_PROGRESS"
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "candidate_id", name="uq_assessment_sessions_campaign_candidate"
        ),
    )
    op.create_index(op.f("ix_assessment_sessions_org_id"), "assessment_sessions", ["org_id"])
    op.create_index(
        op.f("ix_assessment_sessions_campaign_id"), "assessment_sessions", ["campaign_id"]
    )
    op.create_index(
        op.f("ix_assessment_sessions_candidate_id"), "assessment_sessions", ["candidate_id"]
    )
    op.create_foreign_key(
        "fk_assessment_sessions_org_id_organizations",
        "assessment_sessions",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_assessment_sessions_campaign_id_campaigns",
        "assessment_sessions",
        "campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_assessment_sessions_candidate_id_candidates",
        "assessment_sessions",
        "candidates",
        ["candidate_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "question_number", name="uq_assessment_answers_session_question"
        ),
    )
    op.create_index(
        op.f("ix_assessment_answers_session_id"), "assessment_answers", ["session_id"]
    )
    op.create_foreign_key(
        "fk_assessment_answers_session_id_assessment_sessions",
        "assessment_answers",
        "assessment_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "assessment_recordings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("recording_type", _recording_type, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("status", _recording_status, nullable=False, server_default="PENDING"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "recording_type", name="uq_assessment_recordings_session_type"
        ),
    )
    op.create_index(
        op.f("ix_assessment_recordings_session_id"), "assessment_recordings", ["session_id"]
    )
    op.create_foreign_key(
        "fk_assessment_recordings_session_id_assessment_sessions",
        "assessment_recordings",
        "assessment_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_assessment_recordings_session_id_assessment_sessions",
        "assessment_recordings",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_assessment_recordings_session_id"), table_name="assessment_recordings"
    )
    op.drop_table("assessment_recordings")
    _recording_status.drop(op.get_bind(), checkfirst=True)
    _recording_type.drop(op.get_bind(), checkfirst=True)

    op.drop_constraint(
        "fk_assessment_answers_session_id_assessment_sessions",
        "assessment_answers",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_assessment_answers_session_id"), table_name="assessment_answers")
    op.drop_table("assessment_answers")

    op.drop_constraint(
        "fk_assessment_sessions_candidate_id_candidates",
        "assessment_sessions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_assessment_sessions_campaign_id_campaigns", "assessment_sessions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_assessment_sessions_org_id_organizations", "assessment_sessions", type_="foreignkey"
    )
    op.drop_index(op.f("ix_assessment_sessions_candidate_id"), table_name="assessment_sessions")
    op.drop_index(op.f("ix_assessment_sessions_campaign_id"), table_name="assessment_sessions")
    op.drop_index(op.f("ix_assessment_sessions_org_id"), table_name="assessment_sessions")
    op.drop_table("assessment_sessions")
    _assessment_session_status.drop(op.get_bind(), checkfirst=True)
    _assessment_section.drop(op.get_bind(), checkfirst=True)

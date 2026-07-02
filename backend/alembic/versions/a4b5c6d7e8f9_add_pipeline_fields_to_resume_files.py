"""Add pipeline_stage, assigned_recruiter_id, and notes to resume_files

Revision ID: a4b5c6d7e8f9
Revises: d0e1f2a3b4c5
Create Date: 2026-07-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "a4b5c6d7e8f9"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_pipeline_stage = sa.Enum(
    "APPLIED",
    "PARSING",
    "EMBEDDING",
    "RANKED",
    "SHORTLISTED",
    "ASSESSMENT_SENT",
    "INTERVIEW_SCHEDULED",
    "REJECTED",
    "HIRED",
    name="pipelinestage",
)


def upgrade() -> None:
    _pipeline_stage.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "resume_files",
        sa.Column(
            "pipeline_stage",
            _pipeline_stage,
            nullable=False,
            server_default="APPLIED",
        ),
    )
    op.add_column(
        "resume_files",
        sa.Column("assigned_recruiter_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_resume_files_assigned_recruiter_id"),
        "resume_files",
        ["assigned_recruiter_id"],
    )
    op.create_foreign_key(
        "fk_resume_files_assigned_recruiter_id_users",
        "resume_files",
        "users",
        ["assigned_recruiter_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "resume_files",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_files", "notes")
    op.drop_constraint(
        "fk_resume_files_assigned_recruiter_id_users", "resume_files", type_="foreignkey"
    )
    op.drop_index(op.f("ix_resume_files_assigned_recruiter_id"), table_name="resume_files")
    op.drop_column("resume_files", "assigned_recruiter_id")
    op.drop_column("resume_files", "pipeline_stage")
    _pipeline_stage.drop(op.get_bind(), checkfirst=True)

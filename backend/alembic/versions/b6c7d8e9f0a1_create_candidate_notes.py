"""Create candidate_notes

Revision ID: b6c7d8e9f0a1
Revises: a4b5c6d7e8f9
Create Date: 2026-07-06 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_file_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_notes_resume_file_id"), "candidate_notes", ["resume_file_id"]
    )
    op.create_index(op.f("ix_candidate_notes_author_id"), "candidate_notes", ["author_id"])
    op.create_foreign_key(
        "fk_candidate_notes_resume_file_id_resume_files",
        "candidate_notes",
        "resume_files",
        ["resume_file_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_candidate_notes_author_id_users",
        "candidate_notes",
        "users",
        ["author_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_candidate_notes_author_id_users", "candidate_notes", type_="foreignkey")
    op.drop_constraint(
        "fk_candidate_notes_resume_file_id_resume_files", "candidate_notes", type_="foreignkey"
    )
    op.drop_index(op.f("ix_candidate_notes_author_id"), table_name="candidate_notes")
    op.drop_index(op.f("ix_candidate_notes_resume_file_id"), table_name="candidate_notes")
    op.drop_table("candidate_notes")

"""Add candidate_id and error_message to resume_files

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resume_files",
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "resume_files",
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_foreign_key(
        "fk_resume_files_candidate_id",
        "resume_files",
        "candidates",
        ["candidate_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_resume_files_candidate_id", "resume_files", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_files_candidate_id", table_name="resume_files")
    op.drop_constraint(
        "fk_resume_files_candidate_id", "resume_files", type_="foreignkey"
    )
    op.drop_column("resume_files", "error_message")
    op.drop_column("resume_files", "candidate_id")

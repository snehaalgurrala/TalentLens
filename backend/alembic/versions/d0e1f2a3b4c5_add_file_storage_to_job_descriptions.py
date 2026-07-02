"""Add file storage fields to job_descriptions

Revision ID: d0e1f2a3b4c5
Revises: c9d8e7f6a5b4
Create Date: 2026-07-02 00:00:00.000001

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d8e7f6a5b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("job_descriptions", sa.Column("storage_path", sa.String(1024), nullable=True))
    op.add_column("job_descriptions", sa.Column("mime_type", sa.String(127), nullable=True))
    op.add_column("job_descriptions", sa.Column("file_size", sa.BigInteger, nullable=True))


def downgrade() -> None:
    op.drop_column("job_descriptions", "file_size")
    op.drop_column("job_descriptions", "mime_type")
    op.drop_column("job_descriptions", "storage_path")

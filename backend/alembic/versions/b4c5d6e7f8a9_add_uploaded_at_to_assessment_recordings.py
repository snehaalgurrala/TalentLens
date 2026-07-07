"""Add uploaded_at to assessment_recordings

Revision ID: b4c5d6e7f8a9
Revises: a7b8c9d0e1f2
Create Date: 2026-07-07 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "b4c5d6e7f8a9"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessment_recordings",
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_recordings", "uploaded_at")

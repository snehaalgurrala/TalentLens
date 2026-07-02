"""Add review_status and reviewed_at to resume_files

Revision ID: e7f8a9b0c1d2
Revises: b3c4d5e6f7a8
Create Date: 2026-07-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_review_status = sa.Enum("PENDING", "SHORTLISTED", "REJECTED", name="reviewstatus")


def upgrade() -> None:
    _review_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "resume_files",
        sa.Column(
            "review_status",
            _review_status,
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column(
        "resume_files",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resume_files", "reviewed_at")
    op.drop_column("resume_files", "review_status")
    _review_status.drop(op.get_bind(), checkfirst=True)

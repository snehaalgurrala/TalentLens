"""Add is_pinned and mentioned_user_ids to candidate_notes

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-06 00:00:03.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

# revision identifiers
revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_notes",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "candidate_notes",
        sa.Column(
            "mentioned_user_ids", ARRAY(sa.Uuid()), nullable=False, server_default="{}"
        ),
    )


def downgrade() -> None:
    op.drop_column("candidate_notes", "mentioned_user_ids")
    op.drop_column("candidate_notes", "is_pinned")

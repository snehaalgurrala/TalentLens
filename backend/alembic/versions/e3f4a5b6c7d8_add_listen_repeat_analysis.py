"""Add LISTEN_REPEAT analysis_type + semantic_similarity/keyword_coverage columns

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-07 00:00:01.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres forbids ALTER TYPE ... ADD VALUE inside the same transaction
    # that later reads the new value, and env.py wraps the whole migration
    # run in a transaction — autocommit_block() switches this block to
    # AUTOCOMMIT isolation so ADD VALUE commits immediately (see
    # d1e2f3a4b5c6_extend_pipeline_and_activity_enums.py).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE analysistype ADD VALUE IF NOT EXISTS 'LISTEN_REPEAT'")

    op.add_column(
        "assessment_analyses", sa.Column("semantic_similarity", sa.Float(), nullable=True)
    )
    op.add_column(
        "assessment_analyses", sa.Column("keyword_coverage", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    # Postgres cannot drop individual enum values without recreating the
    # type (which would require rewriting every dependent column). This
    # migration's changes are additive-only (a new enum value, two nullable
    # columns), so downgrade is intentionally unsupported — roll forward
    # only, same convention as d1e2f3a4b5c6_extend_pipeline_and_activity_enums.py.
    raise NotImplementedError(
        "Cannot remove the LISTEN_REPEAT analysistype enum value without a full "
        "type rebuild; roll forward only."
    )

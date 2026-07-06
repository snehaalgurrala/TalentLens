"""Extend pipelinestage and activityeventtype enums

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-07-06 00:00:02.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_PIPELINE_STAGE_VALUES = [
    "ASSESSMENT_COMPLETED",
    "INTERVIEW_COMPLETED",
    "OFFER_EXTENDED",
    "OFFER_ACCEPTED",
    "WITHDRAWN",
    "ARCHIVED",
]

_NEW_ACTIVITY_EVENT_TYPE_VALUES = [
    "ARCHIVED",
    "RESTORED",
    "TASK_CREATED",
    "TASK_COMPLETED",
    "TASK_REASSIGNED",
]


def upgrade() -> None:
    # Postgres forbids ALTER TYPE ... ADD VALUE inside the same transaction
    # that later reads the new value, and env.py wraps the whole migration
    # run in a transaction — autocommit_block() switches this block to
    # AUTOCOMMIT isolation so each ADD VALUE commits immediately.
    with op.get_context().autocommit_block():
        for value in _NEW_PIPELINE_STAGE_VALUES:
            op.execute(f"ALTER TYPE pipelinestage ADD VALUE IF NOT EXISTS '{value}'")
        for value in _NEW_ACTIVITY_EVENT_TYPE_VALUES:
            op.execute(f"ALTER TYPE activityeventtype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres cannot drop individual enum values without recreating the
    # type (which would require rewriting every dependent column/table).
    # This feature's new stages are additive-only, so downgrade is
    # intentionally unsupported — roll forward only.
    raise NotImplementedError(
        "Cannot remove pipelinestage/activityeventtype enum values without a full "
        "type rebuild; roll forward only."
    )

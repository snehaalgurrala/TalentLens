"""Add ASSESSMENT_IN_PROGRESS pipeline stage, assessment activity event
types, and the notifications table

Revision ID: f5a6b7c8d9e0
Revises: 75235da0bde6
Create Date: 2026-07-09 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "75235da0bde6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_PIPELINE_STAGE_VALUES = ["ASSESSMENT_IN_PROGRESS"]

_NEW_ACTIVITY_EVENT_TYPE_VALUES = [
    "ASSESSMENT_INVITATION_SENT",
    "ASSESSMENT_STARTED",
    "ASSESSMENT_COMPLETED",
]

_notification_type = sa.Enum("info", "success", "warning", "error", name="notificationtype")


def upgrade() -> None:
    # Postgres forbids ALTER TYPE ... ADD VALUE inside the same transaction
    # that later reads the new value, and env.py wraps the whole migration
    # run in a transaction — autocommit_block() switches this block to
    # AUTOCOMMIT isolation so each ADD VALUE commits immediately. Same
    # pattern as d1e2f3a4b5c6_extend_pipeline_and_activity_enums.py.
    with op.get_context().autocommit_block():
        for value in _NEW_PIPELINE_STAGE_VALUES:
            op.execute(f"ALTER TYPE pipelinestage ADD VALUE IF NOT EXISTS '{value}'")
        for value in _NEW_ACTIVITY_EVENT_TYPE_VALUES:
            op.execute(f"ALTER TYPE activityeventtype ADD VALUE IF NOT EXISTS '{value}'")

    # Do NOT also call _notification_type.create() here: create_table's own
    # column DDL already emits CREATE TYPE for this enum, so a prior
    # explicit .create() call causes a DuplicateObjectError.
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", _notification_type, nullable=False, server_default="info"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resume_file_id", sa.Uuid(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notifications_organization_id"), "notifications", ["organization_id"]
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])
    op.create_index(
        op.f("ix_notifications_resume_file_id"), "notifications", ["resume_file_id"]
    )
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"])
    op.create_foreign_key(
        "fk_notifications_organization_id_organizations",
        "notifications",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_notifications_user_id_users",
        "notifications",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_notifications_resume_file_id_resume_files",
        "notifications",
        "resume_files",
        ["resume_file_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Postgres cannot drop individual enum values without recreating the
    # type (which would require rewriting every dependent column/table).
    # This migration's enum additions are additive-only, so downgrade is
    # intentionally unsupported — roll forward only (same convention as
    # d1e2f3a4b5c6_extend_pipeline_and_activity_enums.py).
    raise NotImplementedError(
        "Cannot remove pipelinestage/activityeventtype enum values without a full "
        "type rebuild; roll forward only."
    )

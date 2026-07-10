"""Create notification_preferences

Revision ID: c4d240f7b2be
Revises: 468d3a792deb
Create Date: 2026-07-09 00:00:03.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "c4d240f7b2be"
down_revision: str | None = "468d3a792deb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BOOL_TRUE = sa.text("true")


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("assessment_completed", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("assessment_started", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("invitation_sent", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("invitation_opened", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("candidate_shortlisted", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("ai_ranking_completed", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("daily_summary", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("weekly_summary", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("email_enabled", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column("in_app_enabled", sa.Boolean, nullable=False, server_default=_BOOL_TRUE),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")

"""Create platform_ai_configs and platform_email_configs (platform-wide singletons)

Revision ID: 468d3a792deb
Revises: a1c99fab352a
Create Date: 2026-07-09 00:00:02.000000

"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

# revision identifiers
revision: str = "468d3a792deb"
down_revision: str | None = "a1c99fab352a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Fixed sentinel IDs — each singleton table always has exactly one row at
# this ID, so "get the config" never needs null-row special-casing anywhere
# downstream.
PLATFORM_AI_CONFIG_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
PLATFORM_EMAIL_CONFIG_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a2")

_email_test_result = sa.Enum("success", "failure", name="emailtestresult")


def upgrade() -> None:
    op.create_table(
        "platform_ai_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default="none"),
        sa.Column("llm_model", sa.String(100), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float, nullable=False, server_default=sa.text("0.7")),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default=sa.text("1024")),
        sa.Column(
            "prompt_logging_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "embedding_model",
            sa.String(200),
            nullable=False,
            server_default="BAAI/bge-large-en-v1.5",
        ),
        sa.Column(
            "similarity_threshold", sa.Float, nullable=False, server_default=sa.text("0.3")
        ),
        sa.Column(
            "reranking_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "explainable_ai_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "retention_policy_days", sa.Integer, nullable=False, server_default=sa.text("365")
        ),
        sa.Column("retention_policy_notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )

    # Do NOT also call _email_test_result.create(...) here — create_table's
    # own column DDL for platform_email_configs already emits CREATE TYPE.
    op.create_table(
        "platform_email_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("smtp_host", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_port", sa.Integer, nullable=False, server_default=sa.text("587")),
        sa.Column("smtp_username", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_password", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_from_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_from_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_tls", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("smtp_ssl", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_configured", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", _email_test_result, nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
    )

    op.bulk_insert(
        sa.table(
            "platform_ai_configs",
            sa.column("id", postgresql.UUID(as_uuid=True)),
        ),
        [{"id": PLATFORM_AI_CONFIG_ID}],
    )
    op.bulk_insert(
        sa.table(
            "platform_email_configs",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("smtp_host", sa.String),
            sa.column("smtp_port", sa.Integer),
            sa.column("smtp_username", sa.String),
            sa.column("smtp_password", sa.String),
            sa.column("smtp_from_email", sa.String),
            sa.column("smtp_from_name", sa.String),
            sa.column("smtp_tls", sa.Boolean),
            sa.column("smtp_ssl", sa.Boolean),
            sa.column("is_configured", sa.Boolean),
        ),
        [
            {
                "id": PLATFORM_EMAIL_CONFIG_ID,
                "smtp_host": settings.SMTP_HOST,
                "smtp_port": settings.SMTP_PORT,
                "smtp_username": settings.SMTP_USERNAME,
                "smtp_password": settings.SMTP_PASSWORD,
                "smtp_from_email": settings.SMTP_FROM_EMAIL,
                "smtp_from_name": settings.SMTP_FROM_NAME,
                "smtp_tls": settings.SMTP_TLS,
                "smtp_ssl": settings.SMTP_SSL,
                "is_configured": bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD),
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("platform_email_configs")
    op.drop_table("platform_ai_configs")
    _email_test_result.drop(op.get_bind(), checkfirst=True)

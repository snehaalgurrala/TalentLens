"""Add organization profile fields

Revision ID: a1498e50de0f
Revises: f5a6b7c8d9e0
Create Date: 2026-07-09 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "a1498e50de0f"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("logo_url", sa.Text(), nullable=True))
    op.add_column("organizations", sa.Column("industry", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("website", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("company_email", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("organizations", sa.Column("address_line1", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("address_line2", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("postal_code", sa.String(20), nullable=True))
    op.add_column("organizations", sa.Column("country", sa.String(100), nullable=True))
    op.add_column(
        "organizations",
        sa.Column(
            "timezone", sa.String(50), nullable=False, server_default="UTC"
        ),
    )
    op.add_column("organizations", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "description")
    op.drop_column("organizations", "timezone")
    op.drop_column("organizations", "country")
    op.drop_column("organizations", "postal_code")
    op.drop_column("organizations", "state")
    op.drop_column("organizations", "city")
    op.drop_column("organizations", "address_line2")
    op.drop_column("organizations", "address_line1")
    op.drop_column("organizations", "phone")
    op.drop_column("organizations", "company_email")
    op.drop_column("organizations", "website")
    op.drop_column("organizations", "industry")
    op.drop_column("organizations", "logo_url")

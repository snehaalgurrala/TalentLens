"""Add campaign metadata fields (job_title, department, hiring manager/
recruiter, employment type, location, experience, salary, openings,
priority, closing date)

Revision ID: c9d8e7f6a5b4
Revises: e7f8a9b0c1d2
Create Date: 2026-07-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision: str = "c9d8e7f6a5b4"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_employment_type = sa.Enum(
    "FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP", "TEMPORARY", name="employmenttype"
)
_campaign_priority = sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="campaignpriority")


def upgrade() -> None:
    _employment_type.create(op.get_bind(), checkfirst=True)
    _campaign_priority.create(op.get_bind(), checkfirst=True)

    op.add_column("campaigns", sa.Column("job_title", sa.String(255), nullable=True))
    op.add_column("campaigns", sa.Column("department", sa.String(120), nullable=True))
    op.add_column(
        "campaigns",
        sa.Column(
            "hiring_manager_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "recruiter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("campaigns", sa.Column("employment_type", _employment_type, nullable=True))
    op.add_column("campaigns", sa.Column("location", sa.String(255), nullable=True))
    op.add_column("campaigns", sa.Column("experience_min_years", sa.Integer, nullable=True))
    op.add_column("campaigns", sa.Column("experience_max_years", sa.Integer, nullable=True))
    op.add_column("campaigns", sa.Column("salary_min", sa.Integer, nullable=True))
    op.add_column("campaigns", sa.Column("salary_max", sa.Integer, nullable=True))
    op.add_column(
        "campaigns",
        sa.Column("openings_count", sa.Integer, nullable=False, server_default="1"),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "priority",
            _campaign_priority,
            nullable=False,
            server_default="MEDIUM",
        ),
    )
    op.add_column("campaigns", sa.Column("closing_date", sa.Date, nullable=True))

    op.create_index("ix_campaigns_department", "campaigns", ["department"])
    op.create_index("ix_campaigns_hiring_manager_id", "campaigns", ["hiring_manager_id"])
    op.create_index("ix_campaigns_recruiter_id", "campaigns", ["recruiter_id"])


def downgrade() -> None:
    op.drop_index("ix_campaigns_recruiter_id", table_name="campaigns")
    op.drop_index("ix_campaigns_hiring_manager_id", table_name="campaigns")
    op.drop_index("ix_campaigns_department", table_name="campaigns")

    op.drop_column("campaigns", "closing_date")
    op.drop_column("campaigns", "priority")
    op.drop_column("campaigns", "openings_count")
    op.drop_column("campaigns", "salary_max")
    op.drop_column("campaigns", "salary_min")
    op.drop_column("campaigns", "experience_max_years")
    op.drop_column("campaigns", "experience_min_years")
    op.drop_column("campaigns", "location")
    op.drop_column("campaigns", "employment_type")
    op.drop_column("campaigns", "recruiter_id")
    op.drop_column("campaigns", "hiring_manager_id")
    op.drop_column("campaigns", "department")
    op.drop_column("campaigns", "job_title")

    _campaign_priority.drop(op.get_bind(), checkfirst=True)
    _employment_type.drop(op.get_bind(), checkfirst=True)

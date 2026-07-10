"""Create assessment_invitations

Revision ID: 75235da0bde6
Revises: f4a5b6c7d8e9
Create Date: 2026-07-08 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "75235da0bde6"
down_revision: str | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_assessment_invitation_status = sa.Enum(
    "PENDING",
    "SENT",
    "OPENED",
    "STARTED",
    "COMPLETED",
    "EXPIRED",
    "REVOKED",
    name="assessmentinvitationstatus",
)


def upgrade() -> None:
    # Do NOT also call _assessment_invitation_status.create() here:
    # with asyncpg, create_table's own column DDL already emits CREATE TYPE
    # for this enum, so a prior explicit .create() call causes a
    # DuplicateObjectError (see d2e3f4a5b6c7_create_assessment_analyses.py).
    op.create_table(
        "assessment_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_session_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "status", _assessment_invitation_status, nullable=False, server_default="PENDING"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_session_id", name="uq_assessment_invitations_assessment_session_id"
        ),
        sa.UniqueConstraint("token_hash", name="uq_assessment_invitations_token_hash"),
    )
    op.create_index(
        op.f("ix_assessment_invitations_organization_id"),
        "assessment_invitations",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_assessment_invitations_assessment_session_id"),
        "assessment_invitations",
        ["assessment_session_id"],
    )
    op.create_index(
        op.f("ix_assessment_invitations_candidate_id"),
        "assessment_invitations",
        ["candidate_id"],
    )
    op.create_index(
        op.f("ix_assessment_invitations_campaign_id"),
        "assessment_invitations",
        ["campaign_id"],
    )
    op.create_foreign_key(
        "fk_assessment_invitations_organization_id_organizations",
        "assessment_invitations",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Constraint name shortened (ref table "sessions" rather than
    # "assessment_sessions") to stay under Postgres' 63-byte identifier limit.
    op.create_foreign_key(
        "fk_assessment_invitations_assessment_session_id_sessions",
        "assessment_invitations",
        "assessment_sessions",
        ["assessment_session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_assessment_invitations_candidate_id_candidates",
        "assessment_invitations",
        "candidates",
        ["candidate_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_assessment_invitations_campaign_id_campaigns",
        "assessment_invitations",
        "campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_assessment_invitations_campaign_id_campaigns",
        "assessment_invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_assessment_invitations_candidate_id_candidates",
        "assessment_invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_assessment_invitations_assessment_session_id_sessions",
        "assessment_invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_assessment_invitations_organization_id_organizations",
        "assessment_invitations",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_assessment_invitations_campaign_id"), table_name="assessment_invitations"
    )
    op.drop_index(
        op.f("ix_assessment_invitations_candidate_id"), table_name="assessment_invitations"
    )
    op.drop_index(
        op.f("ix_assessment_invitations_assessment_session_id"),
        table_name="assessment_invitations",
    )
    op.drop_index(
        op.f("ix_assessment_invitations_organization_id"), table_name="assessment_invitations"
    )
    op.drop_table("assessment_invitations")
    _assessment_invitation_status.drop(op.get_bind(), checkfirst=True)

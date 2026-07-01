"""Add pgvector embedding columns to job_descriptions and parsed_resumes

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── job_descriptions: add vector storage alongside existing status/model columns ──
    # Unsized `vector` column — dimension varies by embedding provider and is
    # tracked explicitly in embedding_dimension (no fixed-width ANN index yet).
    op.add_column("job_descriptions", sa.Column("embedding", Vector(), nullable=True))
    op.add_column(
        "job_descriptions", sa.Column("embedding_dimension", sa.Integer, nullable=True)
    )

    # ── parsed_resumes: add the full embedding lifecycle (previously absent) ──────────
    op.add_column(
        "parsed_resumes",
        sa.Column(
            "embedding_status",
            postgresql.ENUM(
                "PENDING", "GENERATING", "READY", "FAILED",
                name="embeddingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column("parsed_resumes", sa.Column("embedding_model", sa.String(100), nullable=True))
    op.add_column(
        "parsed_resumes",
        sa.Column("embedding_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("parsed_resumes", sa.Column("embedding", Vector(), nullable=True))
    op.add_column(
        "parsed_resumes", sa.Column("embedding_dimension", sa.Integer, nullable=True)
    )


def downgrade() -> None:
    op.drop_column("parsed_resumes", "embedding_dimension")
    op.drop_column("parsed_resumes", "embedding")
    op.drop_column("parsed_resumes", "embedding_generated_at")
    op.drop_column("parsed_resumes", "embedding_model")
    op.drop_column("parsed_resumes", "embedding_status")

    op.drop_column("job_descriptions", "embedding_dimension")
    op.drop_column("job_descriptions", "embedding")

    op.execute("DROP EXTENSION IF EXISTS vector")

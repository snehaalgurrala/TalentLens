"""Create candidate_tasks

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-06 00:00:04.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_task_priority = sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="taskpriority")
_task_status = sa.Enum("OPEN", "IN_PROGRESS", "COMPLETED", name="taskstatus")


def upgrade() -> None:
    # Do NOT also call _task_priority.create()/_task_status.create() here:
    # with asyncpg, create_table's own column DDL already emits CREATE TYPE
    # for each enum (checkfirst=False under the hood), so a prior explicit
    # .create() call causes a DuplicateObjectError on these exact types.
    op.create_table(
        "candidate_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_file_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", _task_priority, nullable=False, server_default="MEDIUM"),
        sa.Column("status", _task_status, nullable=False, server_default="OPEN"),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_tasks_resume_file_id"), "candidate_tasks", ["resume_file_id"]
    )
    op.create_index(op.f("ix_candidate_tasks_assignee_id"), "candidate_tasks", ["assignee_id"])
    op.create_index(op.f("ix_candidate_tasks_status"), "candidate_tasks", ["status"])
    op.create_foreign_key(
        "fk_candidate_tasks_resume_file_id_resume_files",
        "candidate_tasks",
        "resume_files",
        ["resume_file_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_candidate_tasks_assignee_id_users",
        "candidate_tasks",
        "users",
        ["assignee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_candidate_tasks_created_by_id_users",
        "candidate_tasks",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_candidate_tasks_created_by_id_users", "candidate_tasks", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_candidate_tasks_assignee_id_users", "candidate_tasks", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_candidate_tasks_resume_file_id_resume_files", "candidate_tasks", type_="foreignkey"
    )
    op.drop_index(op.f("ix_candidate_tasks_status"), table_name="candidate_tasks")
    op.drop_index(op.f("ix_candidate_tasks_assignee_id"), table_name="candidate_tasks")
    op.drop_index(op.f("ix_candidate_tasks_resume_file_id"), table_name="candidate_tasks")
    op.drop_table("candidate_tasks")
    _task_status.drop(op.get_bind(), checkfirst=True)
    _task_priority.drop(op.get_bind(), checkfirst=True)

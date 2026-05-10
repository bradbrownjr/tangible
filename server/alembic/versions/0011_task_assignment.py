"""Add assigned_to_user_id to standalone_tasks.

Revision ID: 0011_task_assignment
Revises: 0010_standalone_tasks
Create Date: 2026-05-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_task_assignment"
down_revision = "0010_standalone_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("standalone_tasks")}
    if "assigned_to_user_id" not in existing_cols:
        with op.batch_alter_table("standalone_tasks") as batch_op:
            batch_op.add_column(
                sa.Column("assigned_to_user_id", sa.String(26), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("standalone_tasks") as batch_op:
        batch_op.drop_column("assigned_to_user_id")

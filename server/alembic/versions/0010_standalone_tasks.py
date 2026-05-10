"""Add standalone_tasks table and completed_by_user_id to completion tables.

Standalone tasks are one-off to-dos scoped to a collection that are not tied to
any specific item.  completion tables also gain a ``completed_by_user_id``
column so the gamification scoreboard (Phase C) can attribute completions.

Revision ID: 0010_standalone_tasks
Revises: 0009_template_scraper_id
Create Date: 2026-05-09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_standalone_tasks"
down_revision = "0009_template_scraper_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "standalone_tasks" not in existing_tables:
        op.create_table(
            "standalone_tasks",
            sa.Column("id", sa.String(26), primary_key=True),
            sa.Column(
                "collection_id",
                sa.String(26),
                sa.ForeignKey("collections.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "item_id",
                sa.String(26),
                sa.ForeignKey("items.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("title", sa.String(128), nullable=False),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True, index=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "completed_by_user_id",
                sa.String(26),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_by_user_id",
                sa.String(26),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    existing_cols = {c["name"] for c in inspector.get_columns("chore_completions")}
    if "completed_by_user_id" not in existing_cols:
        with op.batch_alter_table("chore_completions") as batch_op:
            batch_op.add_column(
                sa.Column("completed_by_user_id", sa.String(26), nullable=True)
            )

    existing_cols = {c["name"] for c in inspector.get_columns("maintenance_completions")}
    if "completed_by_user_id" not in existing_cols:
        with op.batch_alter_table("maintenance_completions") as batch_op:
            batch_op.add_column(
                sa.Column("completed_by_user_id", sa.String(26), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("maintenance_completions") as batch_op:
        batch_op.drop_column("completed_by_user_id")

    with op.batch_alter_table("chore_completions") as batch_op:
        batch_op.drop_column("completed_by_user_id")

    op.drop_table("standalone_tasks")

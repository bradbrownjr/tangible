"""Phase 12 — completion history and chores."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027_phase12_completion_history_chores"
down_revision = "0026_manual_bundles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_completions",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("task_id", sa.String(26), sa.ForeignKey("maintenance_tasks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(14, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("technician", sa.String(128), nullable=True),
        sa.Column("odometer_reading", sa.Numeric(14, 2), nullable=True),
        sa.Column("hours_reading", sa.Numeric(10, 2), nullable=True),
    )

    op.create_table(
        "chores",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("collection_id", sa.String(26), sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chore_completions",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("chore_id", sa.String(26), sa.ForeignKey("chores.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(14, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("technician", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("chore_completions")
    op.drop_table("chores")
    op.drop_table("maintenance_completions")

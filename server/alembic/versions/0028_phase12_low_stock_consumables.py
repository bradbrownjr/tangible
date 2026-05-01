"""Phase 12 — minimum quantity, consumables linkage."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0028_phase12_low_stock_consumables"
down_revision = "0027_phase12_completion_history_chores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("minimum_quantity", sa.Integer(), nullable=True))

    op.create_table(
        "maintenance_task_consumables",
        sa.Column("task_id", sa.String(26), sa.ForeignKey("maintenance_tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("item_id", sa.String(26), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("depletion_quantity", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("maintenance_task_consumables")
    op.drop_column("items", "minimum_quantity")

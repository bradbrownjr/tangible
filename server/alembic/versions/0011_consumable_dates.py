"""Add consumable date tracking fields to items.

Revision ID: 0011_consumable_dates
Revises: 0010_pantry_grocery
Create Date: 2026-04-30
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_consumable_dates"
down_revision: str | None = "0010_pantry_grocery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add date tracking fields for consumables and perishables (FIFO management).
    # All nullable; intended for pantry/spices/consumable categories.
    op.add_column("items", sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("use_by_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("date_frozen", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("date_opened", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "date_opened")
    op.drop_column("items", "date_frozen")
    op.drop_column("items", "use_by_date")
    op.drop_column("items", "purchased_at")

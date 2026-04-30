"""Rename 'Spices & Pantry' category to 'Pantry'; add items.depleted column.

Revision ID: 0010_pantry_grocery
Revises: 0009_collection_default_category
Create Date: 2026-04-30
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_pantry_grocery"
down_revision: str | None = "0009_collection_default_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename the root category from "Spices & Pantry" to "Pantry".
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE categories SET name = 'Pantry' WHERE slug = 'spices'")
    )

    # Add depleted flag to items (default FALSE so existing rows are unaffected).
    op.add_column(
        "items",
        sa.Column("depleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("items", "depleted")
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE categories SET name = 'Spices & Pantry' WHERE slug = 'spices'")
    )

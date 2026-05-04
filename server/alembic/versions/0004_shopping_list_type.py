"""Add list_type, wish_url, wish_priority to grocery_items.

Revision ID: 0004_shopping_list_type
Revises: 0003_grocery_stores
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_shopping_list_type"
down_revision: str | None = "0003_grocery_stores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect

    bind = op.get_bind()
    existing_cols = [c["name"] for c in sa_inspect(bind).get_columns("grocery_items")]
    existing_indexes = [i["name"] for i in sa_inspect(bind).get_indexes("grocery_items")]

    if "list_type" not in existing_cols:
        op.add_column(
            "grocery_items",
            sa.Column(
                "list_type",
                sa.String(32),
                nullable=False,
                server_default="groceries",
            ),
        )
    if "ix_grocery_items_list_type" not in existing_indexes:
        op.create_index("ix_grocery_items_list_type", "grocery_items", ["list_type"])
    if "wish_url" not in existing_cols:
        op.add_column(
            "grocery_items",
            sa.Column("wish_url", sa.String(2048), nullable=True),
        )
    if "wish_priority" not in existing_cols:
        op.add_column(
            "grocery_items",
            sa.Column("wish_priority", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    op.drop_index("ix_grocery_items_list_type", table_name="grocery_items")
    op.drop_column("grocery_items", "list_type")
    op.drop_column("grocery_items", "wish_url")
    op.drop_column("grocery_items", "wish_priority")

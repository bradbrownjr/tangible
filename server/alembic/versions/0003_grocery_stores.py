"""Add grocery store/aisle tables and category_slug to grocery_items.

Revision ID: 0003_grocery_stores
Revises: 0002_user_locale
Create Date: 2026-05-03
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_grocery_stores"
down_revision: str | None = "0002_user_locale"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    from sqlalchemy import inspect as sa_inspect
    existing_cols = [c["name"] for c in sa_inspect(bind).get_columns("grocery_items")]
    if "category_slug" not in existing_cols:
        op.add_column(
            "grocery_items",
            sa.Column("category_slug", sa.String(120), nullable=True),
        )

    existing_tables = sa_inspect(bind).get_table_names()

    if "grocery_stores" not in existing_tables:
        op.create_table(
            "grocery_stores",
            sa.Column("id", sa.String(26), primary_key=True),
            sa.Column("owner_user_id", sa.String(26), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_grocery_stores_owner_user_id", "grocery_stores", ["owner_user_id"])

    if "grocery_store_aisles" not in existing_tables:
        op.create_table(
            "grocery_store_aisles",
            sa.Column("id", sa.String(26), primary_key=True),
            sa.Column("store_id", sa.String(26), sa.ForeignKey("grocery_stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("position", sa.Integer, nullable=False, server_default="0"),
            sa.Column("category_slugs", sa.Text, nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_grocery_store_aisles_store_id", "grocery_store_aisles", ["store_id"])


def downgrade() -> None:
    op.drop_table("grocery_store_aisles")
    op.drop_table("grocery_stores")
    op.drop_column("grocery_items", "category_slug")

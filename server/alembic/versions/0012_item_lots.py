"""add item lots table

Revision ID: 0012_item_lots
Revises: 0011_consumable_dates
Create Date: 2026-04-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_item_lots"
down_revision: str | None = "0011_consumable_dates"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_lots",
        sa.Column("item_id", sa.String(length=26), nullable=False),
        sa.Column("collection_id", sa.String(length=26), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("use_by_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_frozen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_opened", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_lots_collection_id"), "item_lots", ["collection_id"], unique=False)
    op.create_index(op.f("ix_item_lots_is_active"), "item_lots", ["is_active"], unique=False)
    op.create_index(op.f("ix_item_lots_item_id"), "item_lots", ["item_id"], unique=False)
    op.create_index(op.f("ix_item_lots_use_by_date"), "item_lots", ["use_by_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_item_lots_use_by_date"), table_name="item_lots")
    op.drop_index(op.f("ix_item_lots_item_id"), table_name="item_lots")
    op.drop_index(op.f("ix_item_lots_is_active"), table_name="item_lots")
    op.drop_index(op.f("ix_item_lots_collection_id"), table_name="item_lots")
    op.drop_table("item_lots")

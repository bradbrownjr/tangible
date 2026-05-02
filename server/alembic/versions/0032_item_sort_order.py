"""Add sort_order to items table.

Revision ID: 0032_item_sort_order
Revises: 0031_photo_caption
Create Date: 2026-05-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0032_item_sort_order"
down_revision = "0031_photo_caption"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("sort_order")

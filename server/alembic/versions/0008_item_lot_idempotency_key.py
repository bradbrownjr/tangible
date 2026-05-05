"""Add idempotency_key to item_lots.

Allows the Android offline queue to replay restock calls without creating
duplicate lots. The client generates a UUID when queuing the mutation and
passes it as the Idempotency-Key request header; the server stores it and
returns the existing lot on a repeated key.

Revision ID: 0008_item_lot_idempotency_key
Revises: 0007_item_category_nullable
Create Date: 2026-05-05

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_item_lot_idempotency_key"
down_revision = "0007_item_category_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("item_lots") as batch_op:
        batch_op.add_column(
            sa.Column("idempotency_key", sa.String(128), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_item_lots_idempotency_key", ["idempotency_key"]
        )
        batch_op.create_index("ix_item_lots_idempotency_key", ["idempotency_key"])


def downgrade() -> None:
    with op.batch_alter_table("item_lots") as batch_op:
        batch_op.drop_index("ix_item_lots_idempotency_key")
        batch_op.drop_constraint("uq_item_lots_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_key")

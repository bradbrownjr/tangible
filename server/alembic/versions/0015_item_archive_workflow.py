"""add item archive/disposition fields

Revision ID: 0015_item_archive_workflow
Revises: 0014_item_wanted
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_item_archive_workflow"
down_revision: str | None = "0014_item_wanted"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("items", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("disposition_type", sa.String(length=16), nullable=True))
    op.add_column("items", sa.Column("disposition_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("disposition_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("items", sa.Column("disposition_buyer", sa.String(length=256), nullable=True))
    op.add_column("items", sa.Column("disposition_note", sa.String(length=512), nullable=True))
    op.create_index(op.f("ix_items_archived_at"), "items", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_items_archived_at"), table_name="items")
    op.drop_column("items", "disposition_note")
    op.drop_column("items", "disposition_buyer")
    op.drop_column("items", "disposition_amount")
    op.drop_column("items", "disposition_at")
    op.drop_column("items", "disposition_type")
    op.drop_column("items", "archived_at")

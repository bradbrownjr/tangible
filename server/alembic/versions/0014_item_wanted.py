"""add item wanted flag

Revision ID: 0014_item_wanted
Revises: 0013_item_flags
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_item_wanted"
down_revision: str | None = "0013_item_flags"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("wanted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("items", "wanted")

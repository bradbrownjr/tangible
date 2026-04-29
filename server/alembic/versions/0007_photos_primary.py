"""Add photos.is_primary.

Revision ID: 0007_photos_primary
Revises: 0006_maintenance_parent
Create Date: 2026-04-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_photos_primary"
down_revision: str | None = "0006_maintenance_parent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("photos") as batch:
        batch.add_column(
            sa.Column(
                "is_primary",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("photos") as batch:
        batch.drop_column("is_primary")

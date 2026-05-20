"""Make chores.collection_id nullable and add owner_user_id for standalone chores.

Revision ID: 0003_standalone_chores
Revises: 0002_add_perf_indexes
Create Date: 2026-05-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_standalone_chores"
down_revision: str | None = "0002_add_perf_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make collection_id nullable (standalone chores have no collection)
    with op.batch_alter_table("chores") as batch_op:
        batch_op.alter_column(
            "collection_id",
            existing_type=sa.String(26),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "owner_user_id",
                sa.String(26),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_chores_owner_user_id",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("chores") as batch_op:
        batch_op.drop_constraint("fk_chores_owner_user_id", type_="foreignkey")
        batch_op.drop_column("owner_user_id")
        batch_op.alter_column(
            "collection_id",
            existing_type=sa.String(26),
            nullable=False,
        )

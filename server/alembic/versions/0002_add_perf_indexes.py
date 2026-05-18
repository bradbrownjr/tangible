"""Add performance indexes for alert and low-stock queries.

Revision ID: 0002_add_perf_indexes
Revises: 0001_initial
Create Date: 2026-05-18
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_perf_indexes"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_items_expires_at", "items", ["expires_at"], if_not_exists=True)
    op.create_index("ix_items_use_by_date", "items", ["use_by_date"], if_not_exists=True)
    op.create_index("ix_items_archived_at", "items", ["archived_at"], if_not_exists=True)
    op.create_index("ix_standalone_tasks_completed_at", "standalone_tasks", ["completed_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_standalone_tasks_completed_at", table_name="standalone_tasks", if_exists=True)
    op.drop_index("ix_items_archived_at", table_name="items", if_exists=True)
    op.drop_index("ix_items_use_by_date", table_name="items", if_exists=True)
    op.drop_index("ix_items_expires_at", table_name="items", if_exists=True)

"""Add locale column to users table.

Revision ID: 0002_user_locale
Revises: 0001_initial
Create Date: 2026-05-03
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_user_locale"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 0001 uses Base.metadata.create_all(), so fresh installs already have this
    # column. Only add it when upgrading an older installation.
    bind = op.get_bind()
    from sqlalchemy import inspect as sa_inspect
    existing = [c["name"] for c in sa_inspect(bind).get_columns("users")]
    if "locale" not in existing:
        op.add_column("users", sa.Column("locale", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locale")

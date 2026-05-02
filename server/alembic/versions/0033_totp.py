"""Add TOTP 2FA columns to users.

Revision ID: 0033_totp
Revises: 0032_item_sort_order
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033_totp"
down_revision = "0032_item_sort_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("totp_secret", sa.String(64), nullable=True))
        batch.add_column(sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("totp_backup_codes", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("totp_backup_codes")
        batch.drop_column("totp_enabled")
        batch.drop_column("totp_secret")

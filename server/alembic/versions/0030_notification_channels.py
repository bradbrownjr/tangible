"""Split notification_preferences.enabled into email_enabled / push_enabled / browser_enabled.

Revision ID: 0030_notification_channels
Revises: 0029_notification_preferences
Create Date: 2026-05-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0030_notification_channels"
down_revision = "0029_notification_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the three channel columns, defaulting to True so existing rows stay opted-in.
    op.add_column("notification_preferences", sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("notification_preferences", sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("notification_preferences", sa.Column("browser_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))

    # Migrate: copy old `enabled` value into each channel.
    op.execute("UPDATE notification_preferences SET email_enabled = enabled, push_enabled = enabled, browser_enabled = enabled")

    # Drop the old column.
    op.drop_column("notification_preferences", "enabled")


def downgrade() -> None:
    op.add_column("notification_preferences", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("UPDATE notification_preferences SET enabled = (email_enabled AND push_enabled AND browser_enabled)")
    op.drop_column("notification_preferences", "browser_enabled")
    op.drop_column("notification_preferences", "push_enabled")
    op.drop_column("notification_preferences", "email_enabled")

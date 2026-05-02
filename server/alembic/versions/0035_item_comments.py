"""Add item_comments table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0035_item_comments"
down_revision = "0034_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "item_comments",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column(
            "item_id",
            sa.String(26),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.String(26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "parent_id",
            sa.String(26),
            sa.ForeignKey("item_comments.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("item_comments")

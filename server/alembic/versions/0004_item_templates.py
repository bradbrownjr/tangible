"""Add item_templates table and items.template_id.

Revision ID: 0004_item_templates
Revises: 0003_audit_log
Create Date: 2026-04-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_item_templates"
down_revision: str | None = "0003_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_templates",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "collection_id",
            sa.String(26),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column(
            "created_by",
            sa.String(26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    with op.batch_alter_table("items") as batch:
        batch.add_column(
            sa.Column(
                "template_id",
                sa.String(26),
                sa.ForeignKey(
                    "item_templates.id",
                    ondelete="SET NULL",
                    name="fk_items_template_id",
                ),
                nullable=True,
            )
        )
        batch.create_index("ix_items_template_id", ["template_id"])


def downgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.drop_index("ix_items_template_id")
        batch.drop_constraint("fk_items_template_id", type_="foreignkey")
        batch.drop_column("template_id")
    op.drop_table("item_templates")

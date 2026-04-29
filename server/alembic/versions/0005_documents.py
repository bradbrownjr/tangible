"""Add documents table and items.expires_at.

Revision ID: 0005_documents
Revises: 0004_item_templates
Create Date: 2026-04-29
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_documents"
down_revision: str | None = "0004_item_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "item_id",
            sa.String(26),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("storage_key", sa.String(128), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(256), nullable=False),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column("category", sa.String(32), nullable=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column(
            "uploaded_by",
            sa.String(26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    with op.batch_alter_table("items") as batch:
        batch.add_column(
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_index("ix_items_expires_at", ["expires_at"])


def downgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.drop_index("ix_items_expires_at")
        batch.drop_column("expires_at")
    op.drop_table("documents")

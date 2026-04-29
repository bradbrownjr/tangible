"""Categories taxonomy + items.category_id (replaces items.type enum).

Revision ID: 0008_categories
Revises: 0007_photos_primary
Create Date: 2026-04-29

This migration introduces the curated category tree and switches the
``items`` table from a fixed ``type`` enum to a foreign key into the new
``categories`` table.

Existing item rows are deleted because the project is pre-1.0 and the
new model has no faithful auto-mapping for some legacy enum values.
The ``items.type`` column is dropped.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

from covet.models.base import ulid_str
from covet.seed.catalog import iter_seed_rows

revision: str = "0008_categories"
down_revision: str | None = "0007_photos_primary"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parent_id", sa.String(length=26), nullable=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"],
            ondelete="CASCADE", name="fk_categories_parent_id",
        ),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    # Seed the tree.
    now = datetime.now(UTC)
    bind = op.get_bind()
    slug_to_id: dict[str, str] = {}
    for row in iter_seed_rows():
        cid = ulid_str()
        parent_id = slug_to_id.get(row["parent_slug"]) if row["parent_slug"] else None
        bind.execute(
            sa.text(
                "INSERT INTO categories "
                "(id, created_at, updated_at, parent_id, slug, name, description, "
                "position, is_system, is_active) "
                "VALUES (:id, :ts, :ts, :parent_id, :slug, :name, :description, "
                ":position, :is_system, :is_active)"
            ),
            {
                "id": cid,
                "ts": now,
                "parent_id": parent_id,
                "slug": row["slug"],
                "name": row["name"],
                "description": row["description"],
                "position": row["position"],
                "is_system": True,
                "is_active": True,
            },
        )
        slug_to_id[row["slug"]] = cid

    # Pre-1.0: drop existing items so we can require category_id NOT NULL.
    bind.execute(sa.text("DELETE FROM items"))

    with op.batch_alter_table("items") as batch:
        batch.drop_index("ix_items_type")
        batch.drop_column("type")
        batch.add_column(sa.Column("category_id", sa.String(length=26), nullable=False))
        batch.create_foreign_key(
            "fk_items_category_id", "categories", ["category_id"], ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_items_category_id", ["category_id"])

    # item_templates: replace item_type enum with category_slug string.
    bind.execute(sa.text("DELETE FROM item_templates"))
    with op.batch_alter_table("item_templates") as batch:
        batch.drop_column("item_type")
        batch.add_column(sa.Column("category_slug", sa.String(length=64), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("item_templates") as batch:
        batch.drop_column("category_slug")
        batch.add_column(
            sa.Column("item_type", sa.String(length=32), nullable=False, server_default="generic")
        )

    with op.batch_alter_table("items") as batch:
        batch.drop_index("ix_items_category_id")
        batch.drop_constraint("fk_items_category_id", type_="foreignkey")
        batch.drop_column("category_id")
        batch.add_column(
            sa.Column("type", sa.String(length=32), nullable=False, server_default="generic")
        )
        batch.create_index("ix_items_type", ["type"])
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")

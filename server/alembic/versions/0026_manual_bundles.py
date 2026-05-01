"""Manual / asset bundles (Phase 11)

Adds three tables:
- ``manual_bundles`` — reusable manual libraries scoped to a collection.
- ``bundle_assets`` — binary attachments belonging to a bundle (manual,
  diagram, firmware, service sheet, parts list).
- ``bundle_items`` — many-to-many link between bundles and items.

Revision ID: 0026_manual_bundles
Revises: 0025_locations
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_manual_bundles"
down_revision: str | None = "0025_locations"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "manual_bundles",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "collection_id",
            sa.String(length=26),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # primary_asset_id FK is added after bundle_assets exists (use_alter)
        sa.Column("primary_asset_id", sa.String(length=26), nullable=True),
        sa.Column(
            "created_by",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_manual_bundles_collection_id", "manual_bundles", ["collection_id"])

    op.create_table(
        "bundle_assets",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "bundle_id",
            sa.String(length=26),
            sa.ForeignKey("manual_bundles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "uploaded_by",
            sa.String(length=26),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bundle_assets_bundle_id", "bundle_assets", ["bundle_id"])
    op.create_index("ix_bundle_assets_sha256", "bundle_assets", ["sha256"])

    # Wire the deferred primary_asset_id FK now that bundle_assets exists.
    with op.batch_alter_table("manual_bundles", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_manual_bundles_primary_asset",
            "bundle_assets",
            ["primary_asset_id"],
            ["id"],
            ondelete="SET NULL",
            use_alter=True,
        )

    op.create_table(
        "bundle_items",
        sa.Column(
            "bundle_id",
            sa.String(length=26),
            sa.ForeignKey("manual_bundles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "item_id",
            sa.String(length=26),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_bundle_items_item_id", "bundle_items", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_bundle_items_item_id", table_name="bundle_items")
    op.drop_table("bundle_items")
    with op.batch_alter_table("manual_bundles", schema=None) as batch_op:
        batch_op.drop_constraint("fk_manual_bundles_primary_asset", type_="foreignkey")
    op.drop_index("ix_bundle_assets_sha256", table_name="bundle_assets")
    op.drop_index("ix_bundle_assets_bundle_id", table_name="bundle_assets")
    op.drop_table("bundle_assets")
    op.drop_index("ix_manual_bundles_collection_id", table_name="manual_bundles")
    op.drop_table("manual_bundles")

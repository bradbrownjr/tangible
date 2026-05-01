"""Hierarchical Location tree (Phase 11)

Adds the ``locations`` table (self-referential, collection-scoped) and
replaces the free-text ``items.location`` column with ``items.location_id``.
Existing free-text labels are migrated into top-level ``room`` nodes per
collection so no data is lost.

Revision ID: 0025_locations
Revises: 0024_phase11_sports_tools_pantry
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from covet.models.base import ulid_str

revision: str = "0025_locations"
down_revision: str | None = "0024_phase11_sports_tools_pantry"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _new_id() -> str:
    return ulid_str()


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "collection_id",
            sa.String(length=26),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.String(length=26),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="container"),
        sa.Column("notes", sa.String(length=2048), nullable=True),
        sa.Column("qr_slug", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "collection_id",
            "parent_id",
            "name",
            name="uq_location_collection_parent_name",
        ),
        sa.UniqueConstraint("qr_slug", name="uq_location_qr_slug"),
    )
    op.create_index("ix_locations_collection_id", "locations", ["collection_id"])
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])
    op.create_index("ix_locations_qr_slug", "locations", ["qr_slug"])

    # Add nullable items.location_id alongside the legacy text column so we
    # can copy data, then drop the old column.
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("location_id", sa.String(length=26), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_items_location_id",
            "locations",
            ["location_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_items_location_id", ["location_id"])

    # Data migration: distinct (collection_id, location_text) -> Location row,
    # then point items.location_id at the new row.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT DISTINCT collection_id, location FROM items "
            "WHERE location IS NOT NULL AND TRIM(location) <> ''"
        )
    ).fetchall()
    now = sa.func.current_timestamp()
    for collection_id, label in rows:
        text = (label or "").strip()
        if not text:
            continue
        new_id = _new_id()
        bind.execute(
            sa.text(
                "INSERT INTO locations "
                "(id, collection_id, parent_id, name, kind, notes, qr_slug, "
                "created_at, updated_at) VALUES "
                "(:id, :cid, NULL, :name, 'room', NULL, NULL, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": new_id, "cid": collection_id, "name": text},
        )
        bind.execute(
            sa.text(
                "UPDATE items SET location_id = :lid "
                "WHERE collection_id = :cid AND TRIM(location) = :name"
            ),
            {"lid": new_id, "cid": collection_id, "name": text},
        )
    _ = now  # silence unused-warning in some toolchains

    # Drop the legacy free-text column.
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_column("location")


def downgrade() -> None:
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("location", sa.String(length=256), nullable=True))

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE items SET location = ("
            "  SELECT name FROM locations WHERE locations.id = items.location_id"
            ") WHERE location_id IS NOT NULL"
        )
    )

    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_index("ix_items_location_id")
        batch_op.drop_constraint("fk_items_location_id", type_="foreignkey")
        batch_op.drop_column("location_id")

    op.drop_index("ix_locations_qr_slug", table_name="locations")
    op.drop_index("ix_locations_parent_id", table_name="locations")
    op.drop_index("ix_locations_collection_id", table_name="locations")
    op.drop_table("locations")

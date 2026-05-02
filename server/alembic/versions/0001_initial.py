"""Initial schema (squashed).

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-02

This is a single-shot baseline migration. The pre-1.0 release history
(35 prior incremental migrations) was squashed here on 2026-05-02 to
keep the migration tree minimal for a fresh-install RC. The schema is
created directly from the SQLAlchemy model metadata, then static data
(category taxonomy) is seeded.

If/when 1.0 ships and we have field installs to upgrade, future schema
changes go in new revisions stacked on top of this one.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Import inside the function so Alembic can introspect this module
    # without dragging the application import graph in at module-load time.
    from tangible.db import Base
    from tangible.models import (  # noqa: F401  (registers all tables on Base.metadata)
        Category,
    )
    from tangible.models.base import ulid_str
    from tangible.seed.catalog import iter_seed_rows

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # Seed the curated category taxonomy.
    now = datetime.now(UTC)
    slug_to_id: dict[str, str] = {}
    for row in iter_seed_rows():
        cid = ulid_str()
        parent_id = (
            slug_to_id.get(row["parent_slug"]) if row["parent_slug"] else None
        )
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


def downgrade() -> None:
    from tangible.db import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

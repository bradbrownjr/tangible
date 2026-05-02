"""Location model.

Hierarchical location tree for inventoried items. Each `Location` is a node
in a `Home -> Floor -> Room -> Zone -> Container` tree (the `kind` field is
advisory — arbitrary depth is allowed). Locations are scoped to a single
collection. Items reference a location via `Item.location_id`; deleting a
location sets `Item.location_id = NULL`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from tangible.models.collection import Collection


# Advisory `kind` enum. Stored as a short string for forward compatibility.
LOCATION_KINDS = ("home", "floor", "room", "zone", "container")


class Location(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "parent_id",
            "name",
            name="uq_location_collection_parent_name",
        ),
    )

    collection_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="container")
    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    qr_slug: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    collection: Mapped[Collection] = relationship()
    parent: Mapped[Location | None] = relationship(
        "Location",
        remote_side="Location.id",
        foreign_keys="Location.parent_id",
        back_populates="children",
    )
    children: Mapped[list[Location]] = relationship(
        "Location",
        foreign_keys="Location.parent_id",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

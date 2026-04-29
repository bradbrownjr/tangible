"""Item and ItemType models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from covet.models.collection import Collection
    from covet.models.loan import Loan
    from covet.models.photo import Photo
    from covet.models.tag import ItemTag


class ItemType(enum.StrEnum):
    GENERIC = "generic"
    VINYL = "vinyl"
    CD = "cd"
    TAPE = "tape"
    MOVIE = "movie"
    GAME = "game"
    CONSOLE = "console"
    FUNKO = "funko"
    POKEMON_CARD = "pokemon_card"
    BOOK = "book"
    TOOL = "tool"
    SPICE = "spice"


class Item(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "items"

    collection_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, name="item_type", native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    subtitle: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    current_value: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    acquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # JSON blobs for type-specific fields and external identifiers
    identifiers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    attrs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Optional pointer to the CRDT document for this item.
    doc_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("automerge_docs.id", ondelete="SET NULL"), nullable=True
    )

    # Optional template the item inherits its custom field schema from.
    template_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("item_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )

    collection: Mapped[Collection] = relationship(back_populates="items")
    photos: Mapped[list[Photo]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    tags: Mapped[list[ItemTag]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    loans: Mapped[list[Loan]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

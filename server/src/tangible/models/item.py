"""Item model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
        from tangible.models.category import Category
        from tangible.models.collection import Collection
        from tangible.models.contact import Contact
        from tangible.models.item_comment import ItemComment
        from tangible.models.item_lot import ItemLot
        from tangible.models.loan import Loan
        from tangible.models.location import Location
        from tangible.models.photo import Photo
        from tangible.models.tag import ItemTag
class Item(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "items"

    collection_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("categories.id", ondelete="RESTRICT"),
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
    location_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Consumable-specific dates for FIFO management (e.g. pantry items).
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_by_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_frozen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_opened: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional review flag (cleared on the next edit or explicit dismiss).
    flagged_note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # JSON blobs for type-specific fields and external identifiers
    identifiers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    attrs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Whether the item is depleted (e.g. a pantry item that ran out).
    depleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Minimum quantity threshold for low-stock alerts.
    minimum_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Whether the item is on the wishlist (not yet owned).
    wanted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Archival/disposition tracking for sold/disposed/donated items.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    disposition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    disposition_buyer: Mapped[str | None] = mapped_column(String(256), nullable=True)
    buyer_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    disposition_note: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # User-assigned sort position for manual ordering within a collection.
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Optional pointer to the CRDT document for this item.
    doc_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("automerge_docs.id", ondelete="SET NULL"), nullable=True
    )

    # Optional template the item inherits its custom field schema from.
    template_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("item_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Optional parent for hierarchical / kit-style items.
    parent_id: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True
    )

    collection: Mapped[Collection] = relationship(back_populates="items")
    category: Mapped[Category] = relationship(lazy="joined")
    buyer: Mapped[Contact | None] = relationship()
    location: Mapped[Location | None] = relationship(lazy="joined")
    photos: Mapped[list[Photo]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    tags: Mapped[list[ItemTag]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    loans: Mapped[list[Loan]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    lots: Mapped[list[ItemLot]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    comments: Mapped[list[ItemComment]] = relationship(
        "ItemComment", back_populates="item", cascade="all, delete-orphan", lazy="select"
    )

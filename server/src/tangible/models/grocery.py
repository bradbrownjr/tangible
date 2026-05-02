"""Grocery list entry model.

Shared, ad-hoc shopping items per collection. When linked to an existing
``Item`` (typically a pantry/consumable item), marking it purchased
calls the restock flow on that item.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from tangible.models.collection import Collection
    from tangible.models.item import Item
    from tangible.models.user import User


class GroceryItem(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "grocery_items"

    collection_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When set, marking this entry purchased restocks the linked item.
    linked_item_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    purchased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    purchased_by_user_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    collection: Mapped[Collection] = relationship(lazy="joined")
    created_by: Mapped[User | None] = relationship(
        foreign_keys=[created_by_user_id], lazy="joined"
    )
    purchased_by: Mapped[User | None] = relationship(
        foreign_keys=[purchased_by_user_id], lazy="joined"
    )
    linked_item: Mapped[Item | None] = relationship(lazy="joined")

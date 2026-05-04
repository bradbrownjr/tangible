"""Shopping list models.

Shared, ad-hoc shopping items per collection.  A ``list_type`` field
distinguishes groceries, hardware, home-goods, and wish-list entries so
all four share one table and API.  When linked to an existing ``Item``
(typically a pantry/consumable item), marking it purchased calls the
restock flow on that item.

``ShoppingStore`` and ``ShoppingStoreAisle`` let users map category slugs to
physical store aisles so the shopping feed can be sorted aisle-by-aisle.
"""

from __future__ import annotations

import enum
import json
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


class ListType(enum.StrEnum):
    groceries = "groceries"
    hardware = "hardware"
    home_goods = "home_goods"
    wish_list = "wish_list"


class ShoppingItem(ULIDPrimaryKey, TimestampMixin, Base):
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
    category_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    list_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="groceries", server_default="groceries", index=True
    )
    # Wish-list only fields
    wish_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    wish_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1=low,2=med,3=high

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


class ShoppingStore(ULIDPrimaryKey, TimestampMixin, Base):
    """A named store whose aisles define shopping-list sort order."""

    __tablename__ = "grocery_stores"

    owner_user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    aisles: Mapped[list[ShoppingStoreAisle]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
        order_by="ShoppingStoreAisle.position",
        lazy="select",
    )


class ShoppingStoreAisle(ULIDPrimaryKey, TimestampMixin, Base):
    """One aisle within a store with its associated category slugs."""

    __tablename__ = "grocery_store_aisles"

    store_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("grocery_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # JSON array of category slugs, e.g. '["food.dairy", "food.eggs"]'
    _category_slugs_json: Mapped[str] = mapped_column(
        "category_slugs", Text, nullable=False, default="[]"
    )

    store: Mapped[ShoppingStore] = relationship(back_populates="aisles")

    @property
    def category_slugs(self) -> list[str]:
        return json.loads(self._category_slugs_json or "[]")

    @category_slugs.setter
    def category_slugs(self, value: list[str]) -> None:
        self._category_slugs_json = json.dumps(value)


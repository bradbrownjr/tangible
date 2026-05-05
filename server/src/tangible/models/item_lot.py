"""Inventory lot model for per-package consumable tracking."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from tangible.models.item import Item


class ItemLot(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "item_lots"

    item_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collection_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    use_by_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    date_frozen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_opened: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Opaque key supplied by the client (e.g. Android offline queue UUID) to
    # prevent duplicate lots when a restock is retried after a network failure.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )

    item: Mapped[Item] = relationship(back_populates="lots")

"""Webhook models for item event notifications."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from covet.models.collection import Collection
    from covet.models.user import User


class WebhookEventType(StrEnum):
    """Types of events that trigger webhooks."""

    ITEM_CREATED = "item.created"
    ITEM_UPDATED = "item.updated"
    ITEM_DELETED = "item.deleted"
    ITEM_LOANED = "item.loaned"
    ITEM_RETURNED = "item.returned"
    MAINTENANCE_DUE = "maintenance.due"
    ITEM_ARCHIVED = "item.archived"
    ITEM_RESTORED = "item.restored"


class Webhook(ULIDPrimaryKey, TimestampMixin, Base):
    """Webhook subscription for a collection."""

    __tablename__ = "webhooks"
    __table_args__ = (UniqueConstraint("collection_id", "url", name="uq_webhook_collection_url"),)

    collection_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    events: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="item.created,item.updated,item.deleted",
    )  # CSV of event types
    retry_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Relationships
    collection: Mapped[Collection] = relationship(back_populates="webhooks")
    owner: Mapped[User] = relationship()


class WebhookDelivery(ULIDPrimaryKey, TimestampMixin, Base):
    """Log of webhook delivery attempts."""

    __tablename__ = "webhook_deliveries"

    webhook_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_retry_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    webhook: Mapped[Webhook] = relationship()

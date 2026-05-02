"""Notification preference model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from tangible.models.user import User

# Valid alert kinds that can have notification preferences.
NOTIFICATION_KINDS = (
    "maintenance_due",
    "chore_due",
    "item_use_by",
    "item_expires",
    "lot_use_by",
    "low_stock",
)


class NotificationPreference(ULIDPrimaryKey, TimestampMixin, Base):
    """Per-user, per-kind notification preference across three delivery channels."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", name="uq_notif_pref_user_kind"),
    )

    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    browser_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lead_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    user: Mapped[User] = relationship()

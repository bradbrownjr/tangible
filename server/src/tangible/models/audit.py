"""Audit log entry — append-only record of security-relevant actions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from tangible.models.user import User


class AuditLogEntry(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "audit_log"

    actor_user_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    collection_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    actor: Mapped[User | None] = relationship()

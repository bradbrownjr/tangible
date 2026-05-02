"""Contact model (loan recipients)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey


class Contact(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "contacts"

    owner_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

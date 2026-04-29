"""Document attachments (PDFs, receipts, manuals, warranties)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from covet.models.item import Item
    from covet.models.user import User


class Document(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "documents"

    item_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # category ∈ {"receipt","manual","warranty","other"} - free-form, advisory
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    uploaded_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    item: Mapped[Item] = relationship()
    uploader: Mapped[User | None] = relationship()

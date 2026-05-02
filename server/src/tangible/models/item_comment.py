"""Item comment model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from tangible.models.item import Item
    from tangible.models.user import User


class ItemComment(ULIDPrimaryKey, TimestampMixin, Base):
    """Threaded comment on an item.

    Top-level comments have ``parent_id = None``.  Replies point to another
    ``ItemComment`` via ``parent_id``.  Only one level of nesting is enforced
    by the API (replies to replies are stored flat under the same thread root).
    """

    __tablename__ = "item_comments"

    item_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("item_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    item: Mapped[Item] = relationship(back_populates="comments", lazy="select")
    author: Mapped[User] = relationship(lazy="joined")
    replies: Mapped[list[ItemComment]] = relationship(
        "ItemComment",
        foreign_keys=[parent_id],
        back_populates="parent",
        lazy="select",
    )
    parent: Mapped[ItemComment | None] = relationship(
        "ItemComment",
        foreign_keys=[parent_id],
        back_populates="replies",
        remote_side="ItemComment.id",
    )

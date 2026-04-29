"""Category model: hierarchical taxonomy for items."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    pass


class Category(ULIDPrimaryKey, TimestampMixin, Base):
    """A node in the global item-category tree.

    Categories form a two-level hierarchy: top-level roots (e.g. ``music``,
    ``movies``) and leaves (e.g. ``music.vinyl``, ``movies.bluray``). The
    seed catalog is loaded by Alembic migration ``0008_categories``; users
    may add more leaves under any root via the API.
    """

    __tablename__ = "categories"

    parent_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[Category | None] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list[Category]] = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan"
    )

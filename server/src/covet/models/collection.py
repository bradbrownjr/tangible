"""Collection model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from covet.models.item import Item
    from covet.models.share_link import ShareLink
    from covet.models.user import CollectionMembership, User
    from covet.models.webhook import Webhook


class Collection(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "collections"

    owner_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Slug of a category (root or leaf) the create-item form should default
    # to. Purely a UX hint; items can still belong to any category.
    default_category_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)

    owner: Mapped[User] = relationship(foreign_keys=[owner_id])
    items: Mapped[list[Item]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )
    memberships: Mapped[list[CollectionMembership]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )
    share_links: Mapped[list[ShareLink]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list[Webhook]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )

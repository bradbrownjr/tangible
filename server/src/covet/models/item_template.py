"""ItemTemplate — reusable per-type field schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey
from covet.models.item import ItemType

if TYPE_CHECKING:
    from covet.models.collection import Collection
    from covet.models.user import User


class ItemTemplate(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "item_templates"

    collection_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, name="item_type", native_enum=False, length=32),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # fields: list[{key, label, type, required, default?, options?}]
    # type ∈ {"text","number","boolean","date","url","select"}
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    collection: Mapped[Collection] = relationship()
    creator: Mapped[User | None] = relationship()

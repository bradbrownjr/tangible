"""Manual / asset bundle model.

A `ManualBundle` is a reusable collection of documents (primary manual,
diagrams, firmware, service sheets, parts lists, etc.) that can be linked
to many items. This is intentionally separate from per-item `Document`
attachments so the same manual does not have to be re-uploaded for every
unit of an appliance / power tool / vehicle.

Bundles are scoped to a collection. Assets live in the same content-addressed
store as documents (sha256-keyed under `documents_dir`). A bundle is linked
to items via the `bundle_items` association table. Deleting a bundle
cascades its assets and removes link rows; deleting an item only removes
its link rows (the bundle survives).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from covet.models.collection import Collection
    from covet.models.user import User


# Advisory `kind` enum — stored as a short string for forward compatibility.
BUNDLE_ASSET_KINDS = (
    "manual",
    "diagram",
    "firmware",
    "service",
    "parts",
    "other",
)


class ManualBundle(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "manual_bundles"

    collection_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional pointer to the bundle's "primary" asset (e.g., main user manual).
    primary_asset_id: Mapped[str | None] = mapped_column(
        String(26),
        ForeignKey("bundle_assets.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    collection: Mapped[Collection] = relationship()
    creator: Mapped[User | None] = relationship()
    assets: Mapped[list[BundleAsset]] = relationship(
        "BundleAsset",
        primaryjoin="ManualBundle.id == BundleAsset.bundle_id",
        foreign_keys="BundleAsset.bundle_id",
        cascade="all, delete-orphan",
        order_by="BundleAsset.sort_order",
    )


class BundleAsset(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "bundle_assets"

    bundle_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("manual_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # See BUNDLE_ASSET_KINDS above. Free-form for forward compatibility.
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class BundleItem(Base):
    """Many-to-many link between bundles and items."""

    __tablename__ = "bundle_items"

    bundle_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("manual_bundles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    item_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    )

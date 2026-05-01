"""Item schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    """Fields common to create / update / read."""

    title: str = Field(min_length=1, max_length=512)
    subtitle: str | None = Field(default=None, max_length=512)
    notes: str | None = None
    condition: str | None = None
    quantity: int = Field(default=1, ge=0)
    purchase_price: Decimal | None = None
    current_value: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    acquired_at: datetime | None = None
    expires_at: datetime | None = None
    location: str | None = None
    identifiers: dict[str, Any] = Field(default_factory=dict)
    attrs: dict[str, Any] = Field(default_factory=dict)
    template_id: str | None = None
    parent_id: str | None = None
    depleted: bool = False
    wanted: bool = False
    purchased_at: datetime | None = None
    use_by_date: datetime | None = None
    date_frozen: datetime | None = None
    date_opened: datetime | None = None


class ItemCreate(ItemBase):
    """Create payload.

    Pass either ``category_id`` (canonical) or ``category`` (slug like
    ``music.vinyl``); the API resolves the slug if ``category_id`` is missing.
    """

    collection_id: str
    category_id: str | None = None
    category: str | None = Field(default=None, description="Category slug")


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    subtitle: str | None = None
    notes: str | None = None
    condition: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    purchase_price: Decimal | None = None
    current_value: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    acquired_at: datetime | None = None
    expires_at: datetime | None = None
    location: str | None = None
    identifiers: dict[str, Any] | None = None
    attrs: dict[str, Any] | None = None
    template_id: str | None = None
    parent_id: str | None = None
    category_id: str | None = None
    category: str | None = None
    depleted: bool | None = None
    wanted: bool | None = None
    purchased_at: datetime | None = None
    use_by_date: datetime | None = None
    date_frozen: datetime | None = None
    date_opened: datetime | None = None


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    category_id: str
    category_slug: str | None = None
    primary_photo_id: str | None = None
    flagged_note: str | None = None
    flagged_at: datetime | None = None
    rollup_current_value: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):  # type: ignore[override]
        # Pull slug off the eager-loaded relationship for convenience.
        slug = getattr(getattr(obj, "category", None), "slug", None)
        instance = super().model_validate(obj, *args, **kwargs)
        if slug is not None:
            instance.category_slug = slug
        # Pull primary photo id from the pre-loaded photos relationship (if any).
        photos = getattr(obj, "photos", None)
        if photos is not None:
            primary = next((p for p in photos if p.is_primary), None)
            if primary is not None:
                instance.primary_photo_id = primary.id
        return instance


class ItemFlagUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=256)

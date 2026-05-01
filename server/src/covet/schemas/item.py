"""Item schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

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
    location_id: str | None = None
    identifiers: dict[str, Any] = Field(default_factory=dict)
    attrs: dict[str, Any] = Field(default_factory=dict)
    template_id: str | None = None
    parent_id: str | None = None
    depleted: bool = False
    wanted: bool = False
    archived_at: datetime | None = None
    disposition_type: str | None = None
    disposition_at: datetime | None = None
    disposition_amount: Decimal | None = None
    disposition_buyer: str | None = None
    buyer_id: str | None = None
    disposition_note: str | None = None
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
    location_id: str | None = None
    identifiers: dict[str, Any] | None = None
    attrs: dict[str, Any] | None = None
    template_id: str | None = None
    parent_id: str | None = None
    category_id: str | None = None
    category: str | None = None
    depleted: bool | None = None
    wanted: bool | None = None
    archived_at: datetime | None = None
    disposition_type: str | None = None
    disposition_at: datetime | None = None
    disposition_amount: Decimal | None = None
    disposition_buyer: str | None = None
    buyer_id: str | None = None
    disposition_note: str | None = None
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
    location_path: list[str] | None = None
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
        # Materialize the location path (root-first list of names) for display.
        loc = getattr(obj, "location", None)
        if loc is not None:
            chain: list[str] = []
            cursor = loc
            seen: set[str] = set()
            while cursor is not None and cursor.id not in seen:
                chain.append(cursor.name)
                seen.add(cursor.id)
                cursor = cursor.parent
            instance.location_path = list(reversed(chain))
        # Pull primary photo id from the pre-loaded photos relationship (if any).
        photos = getattr(obj, "photos", None)
        if photos is not None:
            primary = next((p for p in photos if p.is_primary), None)
            if primary is not None:
                instance.primary_photo_id = primary.id
        return instance


class ItemFlagUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=256)


class ItemArchiveUpdate(BaseModel):
    disposition_type: Literal["sold", "disposed", "donated", "archived"] = "archived"
    disposition_at: datetime | None = None
    disposition_amount: Decimal | None = None
    disposition_buyer: str | None = Field(default=None, max_length=256)
    buyer_id: str | None = None
    disposition_note: str | None = Field(default=None, max_length=512)


class ItemBulkPatchRequest(BaseModel):
    collection_id: str
    item_ids: list[str] = Field(min_length=1, max_length=500)
    depleted: bool | None = None
    wanted: bool | None = None
    location_id: str | None = None
    category_id: str | None = None
    category: str | None = None


class ItemBulkTagRequest(BaseModel):
    collection_id: str
    item_ids: list[str] = Field(min_length=1, max_length=500)
    tag_ids: list[str] = Field(min_length=1, max_length=100)
    mode: Literal["add", "remove"] = "add"


class ItemBulkLendRequest(BaseModel):
    collection_id: str
    item_ids: list[str] = Field(min_length=1, max_length=500)
    contact_id: str
    loaned_at: datetime | None = None
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2048)


class ItemBulkArchiveRequest(BaseModel):
    collection_id: str
    item_ids: list[str] = Field(min_length=1, max_length=500)
    disposition_type: Literal["sold", "disposed", "donated", "archived"] = "archived"
    disposition_at: datetime | None = None
    disposition_amount: Decimal | None = None
    disposition_buyer: str | None = Field(default=None, max_length=256)
    disposition_note: str | None = Field(default=None, max_length=512)


class ItemBulkRestoreRequest(BaseModel):
    collection_id: str
    item_ids: list[str] = Field(min_length=1, max_length=500)


class ItemBulkDeleteRequest(BaseModel):
    collection_id: str
    item_ids: list[str] = Field(min_length=1, max_length=500)


class ItemBulkDeleteResponse(BaseModel):
    deleted: int

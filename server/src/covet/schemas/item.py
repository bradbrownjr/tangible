"""Item schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from covet.models.item import ItemType


class ItemBase(BaseModel):
    type: ItemType
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


class ItemCreate(ItemBase):
    collection_id: str


class ItemUpdate(BaseModel):
    type: ItemType | None = None
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


class ItemRead(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    created_at: datetime
    updated_at: datetime

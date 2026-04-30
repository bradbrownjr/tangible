"""Schemas for inventory lots and due-date alerts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ItemLotCreate(BaseModel):
    label: str | None = None
    notes: str | None = None
    quantity: int = Field(default=1, ge=1, le=100000)
    purchased_at: datetime | None = None
    use_by_date: datetime | None = None
    date_frozen: datetime | None = None
    date_opened: datetime | None = None


class ItemLotUpdate(BaseModel):
    label: str | None = None
    notes: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=100000)
    purchased_at: datetime | None = None
    use_by_date: datetime | None = None
    date_frozen: datetime | None = None
    date_opened: datetime | None = None
    is_active: bool | None = None
    consumed_at: datetime | None = None
    disposed_at: datetime | None = None


class ItemLotRead(BaseModel):
    id: str
    item_id: str
    collection_id: str
    label: str | None
    notes: str | None
    quantity: int
    is_active: bool
    purchased_at: datetime | None
    use_by_date: datetime | None
    date_frozen: datetime | None
    date_opened: datetime | None
    consumed_at: datetime | None
    disposed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RestockRequest(ItemLotCreate):
    mark_in_stock: bool = True


class DueAlertRead(BaseModel):
    id: str
    kind: str
    severity: str
    title: str
    collection_id: str
    item_id: str | None = None
    lot_id: str | None = None
    due_at: datetime
    details: str | None = None

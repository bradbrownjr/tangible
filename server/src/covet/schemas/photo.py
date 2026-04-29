"""Photo schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    sha256: str
    mime_type: str
    width: int | None
    height: int | None
    byte_size: int
    sort_order: int
    is_primary: bool
    created_at: datetime


class PhotoUpdate(BaseModel):
    sort_order: int | None = None
    is_primary: bool | None = None


class PhotoFromUrl(BaseModel):
    url: str

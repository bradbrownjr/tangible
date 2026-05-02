"""Document schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    filename: str
    label: str | None
    category: str | None
    mime_type: str
    byte_size: int
    sha256: str
    expires_at: datetime | None
    uploaded_by: str | None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=128)
    category: str | None = Field(default=None, max_length=32)
    expires_at: datetime | None = None

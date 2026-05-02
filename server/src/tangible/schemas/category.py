"""Category schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parent_id: str | None
    slug: str
    name: str
    description: str | None
    position: int
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

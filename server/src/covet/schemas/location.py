"""Location schemas (hierarchical, collection-scoped)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LocationKind = Literal["home", "floor", "room", "zone", "container"]


class LocationBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    kind: LocationKind = "container"
    parent_id: str | None = None
    notes: str | None = Field(default=None, max_length=2048)
    qr_slug: str | None = Field(default=None, max_length=64)


class LocationCreate(LocationBase):
    collection_id: str


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    kind: LocationKind | None = None
    parent_id: str | None = None
    notes: str | None = Field(default=None, max_length=2048)
    qr_slug: str | None = Field(default=None, max_length=64)


class LocationRead(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    children: list[LocationRead] = []
    item_count: int = 0


LocationRead.model_rebuild()

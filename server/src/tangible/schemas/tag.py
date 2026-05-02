"""Tag schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    parent_id: str | None = None
    color: str | None = None


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    parent_id: str | None = None
    color: str | None = None


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    children: list[TagRead] = []


# Rebuild the model to properly handle forward references
TagRead.model_rebuild()

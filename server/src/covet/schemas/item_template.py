"""ItemTemplate schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from covet.models.item import ItemType

FieldType = Literal["text", "number", "boolean", "date", "url", "select"]


class TemplateField(BaseModel):
    key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_][a-z0-9_\-]*$")
    label: str = Field(min_length=1, max_length=128)
    type: FieldType = "text"
    required: bool = False
    default: Any = None
    options: list[str] | None = None  # for type="select"
    help: str | None = Field(default=None, max_length=256)


class ItemTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    item_type: ItemType
    description: str | None = Field(default=None, max_length=512)
    fields: list[TemplateField] = Field(default_factory=list)


class ItemTemplateCreate(ItemTemplateBase):
    pass


class ItemTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    item_type: ItemType | None = None
    description: str | None = Field(default=None, max_length=512)
    fields: list[TemplateField] | None = None


class ItemTemplateRead(ItemTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime

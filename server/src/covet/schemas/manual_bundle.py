"""Pydantic schemas for manual / asset bundles."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BundleAssetKind = Literal[
    "manual", "diagram", "firmware", "service", "parts", "other"
]


class BundleAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bundle_id: str
    sha256: str
    mime_type: str
    byte_size: int
    filename: str
    label: str | None = None
    kind: BundleAssetKind = "other"
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class BundleAssetUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=128)
    kind: BundleAssetKind | None = None
    sort_order: int | None = None


class ManualBundleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None


class ManualBundleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    primary_asset_id: str | None = None


class ManualBundleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    title: str
    description: str | None = None
    primary_asset_id: str | None = None
    created_at: datetime
    updated_at: datetime
    assets: list[BundleAssetRead] = []
    item_ids: list[str] = []

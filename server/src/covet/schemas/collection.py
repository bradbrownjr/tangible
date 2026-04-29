"""Collection / membership / share-link schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["owner", "editor", "viewer"]


class CollectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2048)
    icon: str | None = None
    is_public: bool = False


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    icon: str | None = None
    is_public: bool | None = None


class CollectionRead(CollectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    user_id: str
    role: Role


class MembershipDetail(MembershipRead):
    """Membership row plus enough user info to render a member list."""

    username: str
    email: str | None = None
    display_name: str | None = None


class MembershipCreate(BaseModel):
    """Add a user (by username or email) to a collection."""

    user_identifier: str = Field(min_length=1, max_length=255)
    role: Role = "viewer"


class MembershipUpdate(BaseModel):
    role: Role


class ShareLinkCreate(BaseModel):
    label: str | None = None
    expires_at: datetime | None = None


class ShareLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    slug: str
    label: str | None
    expires_at: datetime | None
    revoked: bool
    created_at: datetime

"""Invitation API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Role = Literal["viewer", "editor"]


class InvitationCreate(BaseModel):
    role: Role = "viewer"
    email: EmailStr | None = None
    expires_at: datetime | None = None


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    role: str
    email: str | None
    expires_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime


class InvitationCreated(InvitationRead):
    """Returned only on creation — includes the one-time plaintext token."""

    token: str = Field(min_length=16)


class InvitationPreview(BaseModel):
    """Preview shown before acceptance — minimal info, no auth required."""

    collection_id: str
    collection_name: str
    role: str
    email: str | None
    expires_at: datetime | None

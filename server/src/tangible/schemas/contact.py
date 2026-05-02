"""Contact schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    email: EmailStr | None = None
    phone: str | None = None
    notes: str | None = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    email: EmailStr | None = None
    phone: str | None = None
    notes: str | None = None


class ContactRead(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str

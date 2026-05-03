"""User-related schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=128)


class UserCreate(UserBase):
    password: str = Field(min_length=12, max_length=255)
    is_admin: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=255)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_admin: bool
    is_active: bool
    locale: str | None = None
    last_login_at: datetime | None
    created_at: datetime
    enrollment_required: bool = False

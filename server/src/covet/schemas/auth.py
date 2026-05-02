"""Auth-related schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from covet.schemas.user import UserRead


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr | None = None
    password: str = Field(min_length=12, max_length=255)
    display_name: str | None = Field(default=None, max_length=128)


class MeUpdate(BaseModel):
    """Self-service profile updates. Cannot change is_admin/is_active."""

    display_name: str | None = Field(default=None, max_length=128)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=12, max_length=255)


class SessionInfo(BaseModel):
    user: UserRead
    expires_at: datetime


class TOTPLoginChallenge(BaseModel):
    """Returned by POST /auth/login when the account has TOTP enabled."""

    totp_required: bool = True
    ticket: str


class TOTPSetupResponse(BaseModel):
    """Returned by POST /auth/totp/setup — contains the provisioning URI and QR PNG."""

    secret: str
    qr_uri: str
    qr_png_b64: str


class TOTPVerifyRequest(BaseModel):
    """Verify a TOTP code to activate 2FA, or to confirm login."""

    code: str = Field(min_length=6, max_length=8)


class TOTPLoginRequest(BaseModel):
    ticket: str
    code: str = Field(min_length=6, max_length=8)


class TOTPStatusResponse(BaseModel):
    enabled: bool
    backup_codes_remaining: int


class TOTPDisableRequest(BaseModel):
    password: str
    totp_code: str | None = None


class AccountDeleteRequest(BaseModel):
    password: str
    totp_code: str | None = None


class TokenInfo(BaseModel):
    id: str
    name: str
    token: str | None = None  # only populated on creation
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class OIDCProviderInfo(BaseModel):
    name: str
    display_name: str
    login_url: str

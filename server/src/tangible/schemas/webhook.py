"""Webhook schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class WebhookCreate(BaseModel):
    """Create a new webhook."""

    url: HttpUrl = Field(..., description="Target URL for webhook delivery")
    secret: str | None = Field(default=None, description="Optional HMAC secret for request signing")
    events: list[str] = Field(
        default=["item.created", "item.updated", "item.deleted"],
        description="List of event types to subscribe to",
    )
    active: bool = Field(default=True, description="Whether the webhook is active")


class WebhookUpdate(BaseModel):
    """Update an existing webhook."""

    url: HttpUrl | None = None
    secret: str | None = None
    events: list[str] | None = None
    active: bool | None = None


class WebhookRead(BaseModel):
    """Read webhook information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    owner_id: str
    url: str
    secret: str | None = None
    active: bool
    events: str  # CSV format
    retry_count: int
    retry_delay_seconds: int
    created_at: str
    updated_at: str


class WebhookDeliveryRead(BaseModel):
    """Read webhook delivery log."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    webhook_id: str
    event_type: str
    status_code: int | None
    success: bool
    error_message: str | None
    attempt_number: int
    next_retry_at: str | None
    created_at: str
    updated_at: str

"""Audit log API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    collection_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    payload: dict[str, Any] | None
    created_at: datetime

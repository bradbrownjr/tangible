"""Append-only audit log service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from covet.models import AuditLogEntry


def log(
    db: DBSession,
    *,
    actor_user_id: str | None,
    action: str,
    collection_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLogEntry:
    """Record a single audit event. Caller is responsible for committing."""
    entry = AuditLogEntry(
        actor_user_id=actor_user_id,
        collection_id=collection_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=payload,
    )
    db.add(entry)
    return entry

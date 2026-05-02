"""Common mixins and ID helpers."""

from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

# A small ULID-like 26-char Crockford base32 ID; sortable by time.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid_str() -> str:
    """Return a 26-char time-sortable identifier."""
    ts_ms = int(time.time() * 1000)
    rand = secrets.randbits(80)
    value = (ts_ms << 80) | rand
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime | None) -> datetime | None:
    """Return ``dt`` with UTC tzinfo attached when naive (SQLite returns naive)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


class ULIDPrimaryKey:
    """Mixin providing a 26-char string primary key."""

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=ulid_str)


class TimestampMixin:
    """Mixin adding ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

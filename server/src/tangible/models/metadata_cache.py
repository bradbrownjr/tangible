"""Cached metadata responses from external providers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey


class MetadataCacheEntry(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "metadata_cache"
    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_metadata_provider_external"),
    )

    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

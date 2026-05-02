"""Scraper registry trust overrides."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from tangible.db import Base
from tangible.models.base import TimestampMixin


class ScraperRegistryPin(TimestampMixin, Base):
    __tablename__ = "scraper_registry_pins"

    entry_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(
        String(26), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

"""Maintenance task, completion history, and chores models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from covet.db import Base
from covet.models.base import TimestampMixin, ULIDPrimaryKey

if TYPE_CHECKING:
    from covet.models.collection import Collection
    from covet.models.item import Item


class MaintenanceTask(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "maintenance_tasks"

    item_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    item: Mapped[Item] = relationship()
    completions: Mapped[list[MaintenanceCompletion]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class MaintenanceCompletion(ULIDPrimaryKey, Base):
    """Immutable record of one maintenance task completion."""

    __tablename__ = "maintenance_completions"

    task_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("maintenance_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    technician: Mapped[str | None] = mapped_column(String(128), nullable=True)
    odometer_reading: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    hours_reading: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    task: Mapped[MaintenanceTask] = relationship(back_populates="completions")


class Chore(ULIDPrimaryKey, TimestampMixin, Base):
    """A recurring household task not tied to a specific item."""

    __tablename__ = "chores"

    collection_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    collection: Mapped[Collection] = relationship()
    completions: Mapped[list[ChoreCompletion]] = relationship(
        back_populates="chore", cascade="all, delete-orphan"
    )


class ChoreCompletion(ULIDPrimaryKey, Base):
    """Immutable record of one chore completion."""

    __tablename__ = "chore_completions"

    chore_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("chores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    technician: Mapped[str | None] = mapped_column(String(128), nullable=True)

    chore: Mapped[Chore] = relationship(back_populates="completions")


class MaintenanceTaskConsumable(Base):
    """Links a maintenance task to an item it depletes when completed."""

    __tablename__ = "maintenance_task_consumables"

    task_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("maintenance_tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    item_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    depletion_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

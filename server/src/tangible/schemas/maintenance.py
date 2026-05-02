"""Maintenance task and chores schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceTaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    notes: str | None = None
    interval_days: int | None = Field(default=None, ge=1, le=36500)
    last_completed_at: datetime | None = None
    next_due_at: datetime | None = None


class MaintenanceTaskCreate(MaintenanceTaskBase):
    pass


class MaintenanceTaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    notes: str | None = None
    interval_days: int | None = Field(default=None, ge=1, le=36500)
    last_completed_at: datetime | None = None
    next_due_at: datetime | None = None


class MaintenanceTaskRead(MaintenanceTaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    created_at: datetime
    updated_at: datetime


class MaintenanceCompletePayload(BaseModel):
    """Optional body for POST /maintenance/{id}/complete."""

    notes: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    technician: str | None = Field(default=None, max_length=128)
    odometer_reading: Decimal | None = Field(default=None, ge=0)
    hours_reading: Decimal | None = Field(default=None, ge=0)


class MaintenanceCompletionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    completed_at: datetime
    notes: str | None
    cost: Decimal | None
    currency: str | None
    technician: str | None
    odometer_reading: Decimal | None
    hours_reading: Decimal | None


# ---------------------------------------------------------------------------
# Chores
# ---------------------------------------------------------------------------


class ChoreBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    notes: str | None = None
    interval_days: int | None = Field(default=None, ge=1, le=36500)
    last_completed_at: datetime | None = None
    next_due_at: datetime | None = None


class ChoreCreate(ChoreBase):
    pass


class ChoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    notes: str | None = None
    interval_days: int | None = Field(default=None, ge=1, le=36500)
    next_due_at: datetime | None = None


class ChoreRead(ChoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    created_at: datetime
    updated_at: datetime


class ChoreCompletePayload(BaseModel):
    """Optional body for POST /chores/{id}/complete."""

    notes: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    technician: str | None = Field(default=None, max_length=128)


class QuickChorePayload(BaseModel):
    """Body for POST /items/{item_id}/quick-chore."""

    chore_name: str = Field(min_length=1, max_length=128)
    interval_days: int | None = Field(default=None, ge=1, le=36500)
    notes: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    technician: str | None = Field(default=None, max_length=128)


class ChoreCompletionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chore_id: str
    completed_at: datetime
    notes: str | None
    cost: Decimal | None
    currency: str | None
    technician: str | None


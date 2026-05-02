"""Loan schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoanBase(BaseModel):
    item_id: str
    contact_id: str
    loaned_at: datetime
    due_at: datetime | None = None
    notes: str | None = None


class LoanCreate(LoanBase):
    pass


class LoanUpdate(BaseModel):
    contact_id: str | None = None
    loaned_at: datetime | None = None
    due_at: datetime | None = None
    returned_at: datetime | None = None
    notes: str | None = None


class LoanRead(LoanBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    returned_at: datetime | None
    created_at: datetime
    updated_at: datetime

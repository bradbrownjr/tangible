"""Admin-only system maintenance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, require_admin
from covet.db import get_session
from covet.models import (
    AuditLogEntry,
    AutomergeChange,
    AutomergeDoc,
    Collection,
    Contact,
    Document,
    Invitation,
    Item,
    ItemLot,
    ItemTag,
    Loan,
    MaintenanceTask,
    MetadataCacheEntry,
    Photo,
    ShareLink,
    Tag,
)

router = APIRouter(prefix="/admin/system", tags=["system"])


class InventoryScrubRequest(BaseModel):
    confirmation: str


class InventoryScrubResponse(BaseModel):
    scrubbed: bool
    deleted_counts: dict[str, int]


_EXPECTED_CONFIRMATION = "SCRUB INVENTORY"


@router.post("/scrub-inventory", response_model=InventoryScrubResponse)
def scrub_inventory_data(
    payload: InventoryScrubRequest,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_admin),
) -> InventoryScrubResponse:
    if payload.confirmation.strip().upper() != _EXPECTED_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Type '{_EXPECTED_CONFIRMATION}' to confirm.",
        )

    delete_models = [
        Photo,
        Document,
        MaintenanceTask,
        Loan,
        ItemTag,
        Tag,
        ItemLot,
        Item,
        Contact,
        ShareLink,
        Invitation,
        Collection,
        AutomergeChange,
        AutomergeDoc,
        MetadataCacheEntry,
        AuditLogEntry,
    ]

    counts: dict[str, int] = {}
    for model in delete_models:
        model_name = model.__tablename__
        counts[model_name] = int(db.scalar(select(func.count()).select_from(model)) or 0)

    for model in delete_models:
        db.execute(delete(model))

    db.commit()
    return InventoryScrubResponse(scrubbed=True, deleted_counts=counts)

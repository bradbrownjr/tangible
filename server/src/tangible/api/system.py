"""Admin-only system maintenance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, require_admin
from tangible.config import Settings, get_settings
from tangible.db import get_session
from tangible.models import (
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
from tangible.services.site_settings import (
    MANAGED_SETTINGS,
    apply_site_settings,
    list_site_settings,
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


# --- Admin site settings ----------------------------------------------------


class SiteSettingRead(BaseModel):
    key: str
    value: str | None
    is_set: bool
    source: str  # "database" | "environment" | "default"
    type: str
    description: str
    sensitive: bool
    section: str
    env_var: str | None


class SiteSettingsUpdate(BaseModel):
    updates: dict[str, str | None]


@router.get("/settings", response_model=list[SiteSettingRead])
def get_site_settings(
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _: AuthContext = Depends(require_admin),
) -> list[SiteSettingRead]:
    """Return all managed settings with their current effective values and source."""
    rows = list_site_settings(db, settings)
    return [SiteSettingRead(**row) for row in rows]


@router.put("/settings", response_model=list[SiteSettingRead])
def update_site_settings(
    payload: SiteSettingsUpdate,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _: AuthContext = Depends(require_admin),
) -> list[SiteSettingRead]:
    """Upsert one or more site settings in the database.

    Pass ``null`` for a key to remove the DB override (revert to env/default).
    Pass ``"***"`` for a sensitive key to leave its value unchanged.
    """
    unknown = [k for k in payload.updates if k not in MANAGED_SETTINGS]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown setting keys: {unknown}",
        )
    apply_site_settings(db, payload.updates)
    rows = list_site_settings(db, settings)
    return [SiteSettingRead(**row) for row in rows]


@router.delete("/settings/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site_setting(
    key: str,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    _: AuthContext = Depends(require_admin),
) -> None:
    """Remove a DB override for a single setting, reverting it to env/default."""
    if key not in MANAGED_SETTINGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown setting key: {key}",
        )
    apply_site_settings(db, {key: None})


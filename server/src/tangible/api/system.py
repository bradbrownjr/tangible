"""Admin-only system maintenance endpoints."""

from __future__ import annotations

import httpx
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


# --- Integration test endpoints ---------------------------------------------


class TestResult(BaseModel):
    ok: bool
    message: str


@router.post("/test-email", response_model=TestResult)
def test_email_connection(
    settings: Settings = Depends(get_settings),
    ctx: AuthContext = Depends(require_admin),
) -> TestResult:
    """Send a test email to the requesting admin to verify SMTP settings."""
    from tangible.email import _smtp_configured, test_smtp_connection

    if not _smtp_configured(settings):
        return TestResult(ok=False, message="SMTP not configured — smtp_host and smtp_from are required")
    to_email = ctx.user.email
    if not to_email:
        return TestResult(ok=False, message="Your admin account has no email address set")
    ok, message = test_smtp_connection(settings, to_email)
    return TestResult(ok=ok, message=message)


_INTEGRATION_TESTS: dict[str, str] = {
    "discogs_token": "discogs",
    "tmdb_api_key": "tmdb",
    "igdb_client_id": "igdb",
    "igdb_client_secret": "igdb",
    "google_books_api_key": "google_books",
    "upcitemdb_key": "upcitemdb",
}


@router.post("/test-integration/{key}", response_model=TestResult)
def test_integration(
    key: str,
    settings: Settings = Depends(get_settings),
    _: AuthContext = Depends(require_admin),
) -> TestResult:
    """Ping the external service for the given integration key to verify it is accepted."""
    if key not in _INTEGRATION_TESTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No test available for key: {key}")

    service = _INTEGRATION_TESTS[key]

    try:
        with httpx.Client(timeout=10) as client:
            if service == "discogs":
                token = settings.discogs_token
                if not token:
                    return TestResult(ok=False, message="discogs_token is not set")
                r = client.get(
                    "https://api.discogs.com/database/search",
                    params={"q": "test", "per_page": "1"},
                    headers={"Authorization": f"Discogs token={token}", "User-Agent": "Tangible/1.0"},
                )
                if r.status_code == 200:
                    return TestResult(ok=True, message="Discogs API key accepted")
                return TestResult(ok=False, message=f"Discogs returned HTTP {r.status_code}")

            if service == "tmdb":
                api_key = settings.tmdb_api_key
                if not api_key:
                    return TestResult(ok=False, message="tmdb_api_key is not set")
                r = client.get(
                    "https://api.themoviedb.org/3/authentication",
                    params={"api_key": api_key},
                )
                if r.status_code == 200:
                    return TestResult(ok=True, message="TMDb API key accepted")
                return TestResult(ok=False, message=f"TMDb returned HTTP {r.status_code}: {r.json().get('status_message', '')}")

            if service == "igdb":
                client_id = settings.igdb_client_id
                client_secret = settings.igdb_client_secret
                if not client_id or not client_secret:
                    return TestResult(ok=False, message="igdb_client_id and igdb_client_secret are both required")
                r = client.post(
                    "https://id.twitch.tv/oauth2/token",
                    params={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"},
                )
                if r.status_code == 200:
                    return TestResult(ok=True, message="IGDB (Twitch) credentials accepted — token obtained")
                return TestResult(ok=False, message=f"IGDB token request returned HTTP {r.status_code}: {r.json().get('message', '')}")

            if service == "google_books":
                api_key = settings.google_books_api_key
                if not api_key:
                    return TestResult(ok=False, message="google_books_api_key is not set")
                r = client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={"q": "test", "maxResults": "1", "key": api_key},
                )
                if r.status_code == 200:
                    return TestResult(ok=True, message="Google Books API key accepted")
                err = r.json().get("error", {}).get("message", "")
                return TestResult(ok=False, message=f"Google Books returned HTTP {r.status_code}: {err}")

            if service == "upcitemdb":
                api_key = settings.upcitemdb_key
                if not api_key:
                    return TestResult(ok=False, message="upcitemdb_key is not set")
                r = client.get(
                    "https://api.upcitemdb.com/prod/trial/lookup",
                    params={"upc": "012345678905"},
                    headers={"user_key": api_key, "key_type": "3scale"},
                )
                if r.status_code in (200, 404):
                    return TestResult(ok=True, message="UPCitemdb API key accepted")
                return TestResult(ok=False, message=f"UPCitemdb returned HTTP {r.status_code}")

    except httpx.TimeoutException:
        return TestResult(ok=False, message="Connection timed out")
    except httpx.RequestError as exc:
        return TestResult(ok=False, message=f"Network error: {exc}")

    return TestResult(ok=False, message="Unknown integration")


"""URL metadata scraping endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, collection_role, require_admin, require_user
from tangible.db import get_session
from tangible.models import ItemTemplate, ScraperRegistryPin
from tangible.schemas import ItemTemplateRead
from tangible.services.metadata import ScrapeError, barcode_lookup, list_adapters, scrape
from tangible.services.scraper_registry import get_entry, list_entries

router = APIRouter(prefix="/metadata", tags=["metadata"])


class ScrapeRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class ScrapeResponse(BaseModel):
    provider: str
    url: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    category: str | None = None
    attrs: dict = {}


class BarcodeLookupRequest(BaseModel):
    barcode: str = Field(min_length=8, max_length=18, pattern=r"^[0-9Xx]+$")


class BarcodeLookupResponse(BaseModel):
    candidates: list[ScrapeResponse]


class RegistryEntryResponse(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    category_slug: str
    homepage: str
    trusted: bool
    fields: list[dict]


class RegistryImportRequest(BaseModel):
    collection_id: str
    entry_ids: list[str] = Field(min_length=1)


class RegistryTrustUpdate(BaseModel):
    trusted: bool


class AdaptersResponse(BaseModel):
    url: list[str]
    barcode: list[str]


@router.post("/barcode", response_model=BarcodeLookupResponse)
def barcode_lookup_endpoint(
    payload: BarcodeLookupRequest,
    _: AuthContext = Depends(require_user),
) -> BarcodeLookupResponse:
    results = barcode_lookup(payload.barcode)
    return BarcodeLookupResponse(
        candidates=[
            ScrapeResponse(
                provider=r.provider,
                url=r.url,
                title=r.title,
                description=r.description,
                image_url=r.image_url,
                category=r.category,
                attrs=r.attrs,
            )
            for r in results
        ]
    )


@router.post("/scrape", response_model=ScrapeResponse)
def scrape_url(
    payload: ScrapeRequest,
    _: AuthContext = Depends(require_user),
) -> ScrapeResponse:
    try:
        result = scrape(payload.url)
    except ScrapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ScrapeResponse(
        provider=result.provider,
        url=result.url,
        title=result.title,
        description=result.description,
        image_url=result.image_url,
        category=result.category,
        attrs=result.attrs,
    )


@router.get("/registry", response_model=list[RegistryEntryResponse])
def scraper_registry(
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_user),
) -> list[RegistryEntryResponse]:
    overrides = {
        pin.entry_id: pin.trusted for pin in db.scalars(select(ScraperRegistryPin)).all()
    }
    return [
        RegistryEntryResponse(
            id=e.id,
            name=e.name,
            provider=e.provider,
            description=e.description,
            category_slug=e.category_slug,
            homepage=e.homepage,
            trusted=overrides.get(e.id, e.trusted),
            fields=e.fields,
        )
        for e in list_entries()
    ]


@router.patch("/registry/{entry_id}/trust", response_model=RegistryEntryResponse)
def set_registry_entry_trust(
    entry_id: str,
    payload: RegistryTrustUpdate,
    db: DBSession = Depends(get_session),
    admin: AuthContext = Depends(require_admin),
) -> RegistryEntryResponse:
    entry = get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registry entry not found")

    pin = db.get(ScraperRegistryPin, entry_id)
    if pin is None:
        pin = ScraperRegistryPin(entry_id=entry_id, trusted=payload.trusted, updated_by=admin.user.id)
        db.add(pin)
    else:
        pin.trusted = payload.trusted
        pin.updated_by = admin.user.id

    db.commit()

    return RegistryEntryResponse(
        id=entry.id,
        name=entry.name,
        provider=entry.provider,
        description=entry.description,
        category_slug=entry.category_slug,
        homepage=entry.homepage,
        trusted=payload.trusted,
        fields=entry.fields,
    )


@router.post("/registry/import", response_model=list[ItemTemplateRead])
def import_registry_entries(
    payload: RegistryImportRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemTemplateRead]:
    role = collection_role(db, auth.user, payload.collection_id)
    if role is None or role not in {"editor", "owner"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing = db.scalars(
        select(ItemTemplate).where(ItemTemplate.collection_id == payload.collection_id)
    ).all()

    imported: list[ItemTemplate] = []
    for entry_id in payload.entry_ids:
        entry = get_entry(entry_id)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown registry entry: {entry_id}",
            )
        marker = f"[registry:{entry.id}]"
        match = next((t for t in existing if (t.description or "").find(marker) >= 0), None)
        if match is not None:
            imported.append(match)
            continue

        desc = f"{entry.description}\n\n{marker}".strip()
        tmpl = ItemTemplate(
            collection_id=payload.collection_id,
            name=entry.name,
            category_slug=entry.category_slug,
            description=desc,
            fields=entry.fields,
            created_by=auth.user.id,
        )
        db.add(tmpl)
        db.flush()
        existing.append(tmpl)
        imported.append(tmpl)

    db.commit()
    for tmpl in imported:
        db.refresh(tmpl)
    return [ItemTemplateRead.model_validate(t) for t in imported]


@router.get("/adapters", response_model=AdaptersResponse)
def list_active_adapters(
    _: AuthContext = Depends(require_admin),
) -> AdaptersResponse:
    """Return the currently active URL and barcode adapters, in priority order.

    Admin only. Useful for verifying that third-party plugin packages have
    been loaded via the ``tangible.scraper_adapter`` / ``tangible.barcode_adapter``
    entry-point groups.
    """
    info = list_adapters()
    return AdaptersResponse(url=info["url"], barcode=info["barcode"])

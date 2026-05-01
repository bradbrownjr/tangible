"""Import + backup endpoints."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from covet.db import get_session
from covet.importers import CLZ_IMPORTERS, BackupStats, CSVImporter, export_user, import_backup
from covet.models import Category, Item
from covet.services.categories import resolve_slug

router = APIRouter(prefix="/imports", tags=["imports"])

_EDITOR_ROLES = {"editor", "owner"}


def _check_collection(db: DBSession, auth: AuthContext, collection_id: str) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in _EDITOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _check_collection_read(db: DBSession, auth: AuthContext, collection_id: str) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _persist_items(
    db: DBSession, *, collection_id: str, items_data: list[dict]
) -> int:
    from covet.api.locations import resolve_or_create as _resolve_loc

    count = 0
    slug_cache: dict[str, str] = {}
    ref_to_item: dict[str, Item] = {}
    pending_parent_refs: list[tuple[Item, str]] = []
    for raw in items_data:
        slug = raw["category_slug"]
        if slug not in slug_cache:
            slug_cache[slug] = resolve_slug(db, slug).id

        identifiers = dict(raw.get("identifiers", {}) or {})
        item_ref = identifiers.pop("__csv_item_ref", None)
        parent_ref = identifiers.pop("__csv_parent_ref", None)

        location_id = _resolve_loc(
            db, collection_id=collection_id, name=raw.get("location")
        )

        item = Item(
            collection_id=collection_id,
            category_id=slug_cache[slug],
            title=raw["title"],
            subtitle=raw.get("subtitle"),
            notes=raw.get("notes"),
            condition=raw.get("condition"),
            quantity=int(raw.get("quantity", 1)),
            purchase_price=raw.get("purchase_price"),
            current_value=raw.get("current_value"),
            currency=raw.get("currency"),
            location_id=location_id,
            identifiers=identifiers,
            attrs=raw.get("attrs", {}) or {},
        )
        db.add(item)
        db.flush()

        if item_ref is not None and str(item_ref).strip():
            ref_to_item[str(item_ref)] = item
        if parent_ref is not None and str(parent_ref).strip():
            pending_parent_refs.append((item, str(parent_ref)))

        count += 1

    for item, parent_ref in pending_parent_refs:
        parent = ref_to_item.get(parent_ref)
        if parent is not None:
            item.parent_id = parent.id

    db.commit()
    return count


@router.get("/csv/export", status_code=status.HTTP_200_OK)
def export_csv(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> PlainTextResponse:
    _check_collection_read(db, auth, collection_id)

    rows = db.execute(
        select(Item, Category.slug)
        .join(Category, Item.category_id == Category.id)
        .where(Item.collection_id == collection_id)
        .order_by(Item.created_at, Item.id)
    ).all()

    ref_by_item_id: dict[str, str] = {}
    for index, (item, _) in enumerate(rows, start=1):
        ref_by_item_id[item.id] = f"item-{index}"

    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Item ref",
            "Parent ref",
            "Category",
            "Title",
            "Subtitle",
            "Notes",
            "Quantity",
            "Condition",
            "Location",
            "Currency",
            "Purchase price",
            "Current value",
            "Identifiers JSON",
            "Attrs JSON",
        ]
    )
    for item, category_slug in rows:
        writer.writerow(
            [
                ref_by_item_id[item.id],
                ref_by_item_id.get(item.parent_id, "") if item.parent_id else "",
                category_slug,
                item.title,
                item.subtitle or "",
                item.notes or "",
                item.quantity,
                item.condition or "",
                (item.location.name if item.location else ""),
                item.currency or "",
                item.purchase_price if item.purchase_price is not None else "",
                item.current_value if item.current_value is not None else "",
                json.dumps(item.identifiers or {}),
                json.dumps(item.attrs or {}),
            ]
        )

    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": 'attachment; filename="covet-export.csv"'},
    )


@router.post("/clz", status_code=status.HTTP_200_OK)
async def import_clz(
    collection_id: Annotated[str, Form(...)],
    flavor: Annotated[str, Form(..., description="One of: clz-movie/music/book/comic/game")],
    file: Annotated[UploadFile, File(...)],
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    _check_collection(db, auth, collection_id)
    importer_cls = CLZ_IMPORTERS.get(flavor)
    if importer_cls is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown CLZ flavor: {flavor}",
        )
    importer = importer_cls()
    result = importer.parse(file.file)
    inserted = _persist_items(
        db,
        collection_id=collection_id,
        items_data=[
            {
                "category_slug": i.category_slug,
                "title": i.title,
                "subtitle": i.subtitle,
                "notes": i.notes,
                "condition": i.condition,
                "quantity": i.quantity,
                "purchase_price": i.purchase_price,
                "current_value": i.current_value,
                "currency": i.currency,
                "location": i.location,
                "identifiers": i.identifiers,
                "attrs": i.attrs,
            }
            for i in result.items
        ],
    )
    return {"imported": inserted, "warnings": result.warnings}


@router.post("/csv", status_code=status.HTTP_200_OK)
async def import_csv(
    collection_id: Annotated[str, Form(...)],
    mapping: Annotated[str, Form(..., description="JSON object: csv_header → target field")],
    file: Annotated[UploadFile, File(...)],
    category: Annotated[
        str | None,
        Form(description="Default category slug when CSV rows omit category."),
    ] = None,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    _check_collection(db, auth, collection_id)
    try:
        column_map = json.loads(mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"mapping is not valid JSON: {exc}",
        ) from exc
    if not isinstance(column_map, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mapping must be a JSON object",
        )
    importer = CSVImporter(default_category_slug=category, mapping=column_map)
    result = importer.parse(file.file)
    inserted = _persist_items(
        db,
        collection_id=collection_id,
        items_data=[
            {
                "category_slug": i.category_slug,
                "title": i.title,
                "subtitle": i.subtitle,
                "notes": i.notes,
                "condition": i.condition,
                "quantity": i.quantity,
                "purchase_price": i.purchase_price,
                "current_value": i.current_value,
                "currency": i.currency,
                "location": i.location,
                "identifiers": i.identifiers,
                "attrs": i.attrs,
            }
            for i in result.items
        ],
    )
    return {"imported": inserted, "warnings": result.warnings}


@router.get("/csv/template", status_code=status.HTTP_200_OK)
def csv_template(category: str = "movies.dvd") -> PlainTextResponse:
    """Download a starter CSV with the column headers Covet's CSV importer
    expects out of the box. Users fill it in and upload it back through the
    CSV importer with the matching default mapping.
    """
    headers = [
        "Title",
        "Subtitle",
        "Year",
        "Notes",
        "Quantity",
        "Condition",
        "Location",
        "Currency",
        "Purchase price",
        "Current value",
        "Barcode",
    ]
    samples: dict[str, list[str]] = {
        "movies.dvd": ["The Matrix", "", "1999", "", "1", "good", "", "USD", "", "", ""],
        "movies.bluray": ["Blade Runner 2049", "", "2017", "", "1", "good", "", "USD", "", "", ""],
        "music.cd": ["OK Computer", "Radiohead", "1997", "", "1", "good", "", "USD", "", "", ""],
        "music.vinyl": ["Kind of Blue", "Miles Davis", "1959", "", "1", "good", "", "USD", "", "", ""],
        "books.print": ["Dune", "Frank Herbert", "1965", "", "1", "good", "", "USD", "", "", ""],
        "books.comic": ["Saga #1", "", "2012", "", "1", "good", "", "USD", "", "", ""],
        "games.software": ["Hades", "", "2020", "", "1", "good", "", "USD", "", "", ""],
    }
    sample = samples.get(category, ["Item name", "", "", "", "1", "", "", "", "", "", ""])

    import csv
    import io

    safe_name = category.replace(".", "-")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerow(sample)
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"content-disposition": f'attachment; filename="covet-{safe_name}-template.csv"'},
    )


@router.post("/list", status_code=status.HTTP_200_OK)
async def import_list(
    collection_id: Annotated[str, Form()],
    category: Annotated[str, Form(description="Category slug, e.g. 'other.generic'.")],
    titles: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    """Quick-add a flat list of titles. Each non-blank line becomes one item
    in ``category`` with only ``title`` set. Lines beginning with '#' are
    treated as comments and skipped. Either paste the list in ``titles`` or
    attach a plain-text ``file``.
    """
    _check_collection(db, auth, collection_id)
    raw_text = titles or ""
    if file is not None:
        raw_text += "\n" + (await file.read()).decode("utf-8", errors="replace")
    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No titles provided. Paste a list or attach a .txt file.",
        )
    inserted = _persist_items(
        db,
        collection_id=collection_id,
        items_data=[{"category_slug": category, "title": t} for t in lines],
    )
    return {"imported": inserted, "warnings": []}


@router.get("/backup", status_code=status.HTTP_200_OK)
def download_backup(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> JSONResponse:
    payload = export_user(db, user=auth.user)
    return JSONResponse(
        payload,
        headers={"content-disposition": 'attachment; filename="covet-backup.json"'},
    )


@router.post("/restore", status_code=status.HTTP_200_OK)
async def upload_backup(
    file: Annotated[UploadFile, File(...)],
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> BackupStats:
    raw = await file.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backup file: {exc}",
        ) from exc
    try:
        return import_backup(db, user=auth.user, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

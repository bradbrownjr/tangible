"""Item endpoints."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from decimal import Decimal

import qrcode  # type: ignore[import]
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import String, asc, cast, delete, desc, func, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload
from unidecode import unidecode

from tangible.api.item_templates import validate_attrs
from tangible.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from tangible.db import get_session
from tangible.models import (
    Category,
    Collection,
    CollectionMembership,
    Contact,
    Document,
    Item,
    ItemTag,
    ItemTemplate,
    Loan,
    Location,
    ShoppingItem,
    Tag,
)
from tangible.schemas import (
    ItemArchiveUpdate,
    ItemBulkArchiveRequest,
    ItemBulkDeleteRequest,
    ItemBulkDeleteResponse,
    ItemBulkLendRequest,
    ItemBulkPatchRequest,
    ItemBulkRestoreRequest,
    ItemBulkTagRequest,
    ItemCreate,
    ItemFlagUpdate,
    ItemRead,
    ItemUpdate,
    LoanRead,
    TagRead,
)
from tangible.services import audit
from tangible.services.categories import resolve_slug, subtree_ids
from tangible.services.metadata import ScrapeResult, barcode_lookup
from tangible.services.qr_labels import generate_qr_codes_pdf

router = APIRouter(prefix="/items", tags=["items"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _validate_parent(
    db: DBSession, parent_id: str, collection_id: str, child_id: str | None
) -> None:
    if child_id is not None and parent_id == child_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Item cannot be its own parent",
        )
    parent = db.get(Item, parent_id)
    if parent is None or parent.collection_id != collection_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parent item not found in this collection",
        )
    # Walk ancestors to detect cycles.
    seen: set[str] = set()
    cursor: Item | None = parent
    while cursor is not None and cursor.parent_id is not None:
        if cursor.parent_id in seen or cursor.parent_id == child_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parent assignment would create a cycle",
            )
        seen.add(cursor.parent_id)
        cursor = db.get(Item, cursor.parent_id)


def _validate_location(db: DBSession, location_id: str, collection_id: str) -> None:
    loc = db.get(Location, location_id)
    if loc is None or loc.collection_id != collection_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location not found in this collection",
        )


def _apply_sort(
    stmt,
    *,
    sort_by: str,
    sort_dir: str,
    sort_attr: str | None,
):
    direction = asc if sort_dir == "asc" else desc

    if sort_by == "sort_order":
        return stmt.order_by(direction(Item.sort_order), Item.title, Item.id)

    if sort_by == "title":
        return stmt.order_by(direction(Item.title), Item.id)

    if sort_by == "value":
        return stmt.order_by(
            Item.current_value.is_(None),
            direction(Item.current_value),
            Item.title,
            Item.id,
        )

    if sort_by == "acquired_at":
        acquired = func.coalesce(Item.acquired_at, Item.purchased_at)
        return stmt.order_by(acquired.is_(None), direction(acquired), Item.title, Item.id)

    if sort_by == "attr":
        if not sort_attr:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="sort_attr is required when sort_by=attr",
            )
        attr_value = Item.attrs[sort_attr].as_string()
        return stmt.order_by(attr_value.is_(None), direction(attr_value), Item.title, Item.id)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="sort_by must be one of: sort_order, title, value, acquired_at, attr",
    )


def _compute_rollup_values(db: DBSession, collection_id: str) -> dict[str, Decimal]:
    rows = db.execute(
        select(Item.id, Item.parent_id, Item.current_value).where(Item.collection_id == collection_id)
    ).all()

    children_by_parent: dict[str, list[str]] = {}
    own_values: dict[str, Decimal] = {}
    for item_id, parent_id, current_value in rows:
        own_values[item_id] = current_value if current_value is not None else Decimal("0")
        if parent_id is not None:
            children_by_parent.setdefault(parent_id, []).append(item_id)

    memo: dict[str, Decimal] = {}

    def effective_value(item_id: str) -> Decimal:
        cached = memo.get(item_id)
        if cached is not None:
            return cached
        children = children_by_parent.get(item_id)
        if children:
            total = Decimal("0")
            for child_id in children:
                total += effective_value(child_id)
            memo[item_id] = total
            return total
        value = own_values.get(item_id, Decimal("0"))
        memo[item_id] = value
        return value

    rollups: dict[str, Decimal] = {}
    for parent_id in children_by_parent:
        rollups[parent_id] = effective_value(parent_id)
    return rollups


def _to_item_read(item: Item, rollups: dict[str, Decimal]) -> ItemRead:
    dto = ItemRead.model_validate(item)
    if item.id in rollups:
        dto.rollup_current_value = rollups[item.id]
    return dto


@router.get("", response_model=list[ItemRead])
def list_items(
    collection_id: str = Query(...),
    category: str | None = Query(default=None, description="Category slug, e.g. 'music.vinyl'."),
    category_subtree: str | None = Query(
        default=None,
        description="Top-level category slug; matches the root and all of its children.",
    ),
    search: str | None = None,
    include_archived: bool = Query(
        default=False,
        description="Include archived items in results.",
    ),
    archived: bool | None = Query(
        default=None,
        description="When include_archived=true, optionally narrow to archived=true/false.",
    ),
    depleted: bool | None = Query(default=None, description="Filter by depleted status."),
    wanted: bool | None = Query(default=None, description="Filter by wanted status."),
    flagged: bool | None = Query(default=None, description="Filter by review flag status."),
    tag_ids: list[str] = Query(default=[], description="Filter to items with these tag IDs."),
    tag_mode: str = Query(
        default="all",
        description="Tag match mode: 'all' (AND, default) or 'any' (OR).",
    ),
    sort_by: str = Query(
        default="title",
        description="Sort key: title, value (current_value), acquired_at, or attr.",
    ),
    sort_dir: str = Query(default="asc", description="Sort direction: asc or desc."),
    sort_attr: str | None = Query(
        default=None,
        description="Custom attribute key, required when sort_by=attr.",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    rollups = _compute_rollup_values(db, collection_id)
    stmt = select(Item).where(Item.collection_id == collection_id)
    if category_subtree:
        try:
            ids = subtree_ids(db, category_subtree)
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        stmt = stmt.where(Item.category_id.in_(ids))
    elif category:
        try:
            cat = resolve_slug(db, category)
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        stmt = stmt.where(Item.category_id == cat.id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Item.title.ilike(like),
                Item.subtitle.ilike(like),
                Item.notes.ilike(like),
                cast(Item.attrs, String).ilike(like),
                cast(Item.identifiers, String).ilike(like),
            )
        )
    if not include_archived:
        stmt = stmt.where(Item.archived_at.is_(None))
    elif archived is not None:
        if archived:
            stmt = stmt.where(Item.archived_at.is_not(None))
        else:
            stmt = stmt.where(Item.archived_at.is_(None))
    if depleted is not None:
        stmt = stmt.where(Item.depleted.is_(depleted))
    if wanted is not None:
        stmt = stmt.where(Item.wanted.is_(wanted))
    if flagged is not None:
        if flagged:
            stmt = stmt.where(Item.flagged_at.is_not(None))
        else:
            stmt = stmt.where(Item.flagged_at.is_(None))
    if tag_ids:
        if tag_mode not in {"all", "any"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tag_mode must be 'all' or 'any'",
            )
        if tag_mode == "any":
            stmt = stmt.where(
                Item.id.in_(
                    select(ItemTag.item_id).where(ItemTag.tag_id.in_(tag_ids))
                )
            )
        else:
            for tid in tag_ids:
                stmt = stmt.where(
                    Item.id.in_(
                        select(ItemTag.item_id).where(ItemTag.tag_id == tid)
                    )
                )
    if sort_dir not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort_dir must be one of: asc, desc",
        )
    stmt = stmt.options(selectinload(Item.photos))
    stmt = _apply_sort(stmt, sort_by=sort_by, sort_dir=sort_dir, sort_attr=sort_attr)
    stmt = stmt.limit(limit).offset(offset)
    return [_to_item_read(item, rollups) for item in db.scalars(stmt)]


class ItemReorderEntry(BaseModel):
    id: str
    sort_order: int


@router.put("/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_items(
    collection_id: str = Query(...),
    payload: list[ItemReorderEntry] = ...,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    """Batch-update sort_order for items in a collection (for drag-to-reorder)."""
    _require_role(db, auth, collection_id, _EDITOR_ROLES)
    ids = [e.id for e in payload]
    owned = {
        r.id
        for r in db.scalars(
            select(Item).where(Item.collection_id == collection_id).where(Item.id.in_(ids))
        )
    }
    for entry in payload:
        if entry.id not in owned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Item {entry.id!r} not found in collection",
            )
        db.execute(
            Item.__table__.update()
            .where(Item.id == entry.id)
            .values(sort_order=entry.sort_order)
        )
    db.commit()


class AiPrefillRequest(BaseModel):
    """Request body for AI-assisted item pre-fill."""

    barcode: str | None = None
    collection_id: str | None = None


class AiPrefillResponse(BaseModel):
    """Suggested field values for a new item.

    All fields are optional — callers should pre-fill only those that are
    non-null and let the user confirm or edit before saving.
    """

    title: str | None = None
    subtitle: str | None = None
    category_slug: str | None = None
    attrs: dict | None = None
    source: str | None = None


@router.post("/ai-prefill", response_model=AiPrefillResponse)
def ai_prefill(
    payload: AiPrefillRequest,
    auth: AuthContext = Depends(require_user),
) -> AiPrefillResponse:
    """Suggest item field values from a barcode.

    Queries the enabled barcode adapters (Open Library, MusicBrainz,
    Open Food Facts, Google Books) and returns the best-match title,
    category, and attributes.  Returns an empty response if no match is
    found — the client should treat any field as an optional hint.

    Image-based prefill requires an external vision API that is not
    bundled; this endpoint only supports barcode lookup today.
    """
    if not payload.barcode:
        return AiPrefillResponse()

    try:
        results: list[ScrapeResult] = barcode_lookup(payload.barcode)
    except Exception:
        return AiPrefillResponse()

    if not results:
        return AiPrefillResponse()

    best = results[0]
    return AiPrefillResponse(
        title=best.title,
        subtitle=best.description,
        category_slug=best.category,
        attrs=best.attrs or None,
        source=best.provider,
    )


_SEARCH_FIELDS = {"all", "title", "brand", "category", "notes", "barcode", "serial", "tag"}
_BARCODE_KEYS = ("barcode", "ean", "ean13", "ean8", "upc", "upc_a", "upc_e", "isbn", "qr")
_SERIAL_KEYS = ("serial", "sn", "serial_number", "service_tag", "imei")


def _item_field_text(
    item: Item,
    field: str,
    doc_text_by_item: dict[str, list[str]],
    category_slug_by_id: dict[str, str],
    tag_names_by_item: dict[str, list[str]],
) -> str:
    """Return the substring of `item` that should be matched for `field`."""
    if field == "title":
        return item.title or ""
    if field == "brand":
        attrs = item.attrs or {}
        brand = attrs.get("brand") or attrs.get("manufacturer") or attrs.get("maker") or ""
        return str(brand)
    if field == "category":
        return category_slug_by_id.get(item.category_id or "", "") or ""
    if field == "notes":
        return " ".join(filter(None, [item.subtitle or "", item.notes or ""]))
    if field == "barcode":
        ids = item.identifiers or {}
        return " ".join(str(ids[k]) for k in _BARCODE_KEYS if ids.get(k))
    if field == "serial":
        ids = item.identifiers or {}
        attrs = item.attrs or {}
        parts = [str(ids[k]) for k in _SERIAL_KEYS if ids.get(k)]
        parts += [str(attrs[k]) for k in _SERIAL_KEYS if attrs.get(k)]
        return " ".join(parts)
    if field == "tag":
        return " ".join(tag_names_by_item.get(item.id, []))
    # all
    fields = [
        item.title or "",
        item.subtitle or "",
        item.notes or "",
        " ".join(str(v) for v in (item.attrs or {}).values()),
        " ".join(str(v) for v in (item.identifiers or {}).values()),
        " ".join(doc_text_by_item.get(item.id, [])),
        category_slug_by_id.get(item.category_id or "", "") or "",
        " ".join(tag_names_by_item.get(item.id, [])),
    ]
    return " ".join(fields)


@router.get("/search", response_model=list[ItemRead])
def search_items(
    q: str = Query(..., min_length=1, max_length=256, description="Search query"),
    field: str = Query(default="all", description="Field to search in"),
    include_archived: bool = Query(default=False, description="Include archived/disposed items"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    """Global search across all items in user's accessible collections.

    Supports fuzzy matching with accent-folding (é matches e, etc).
    The `field` parameter narrows the search to a single attribute:
    `all`, `title`, `brand`, `category`, `notes`, `barcode`, `serial`, or `tag`.
    """
    if field not in _SEARCH_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"field must be one of {sorted(_SEARCH_FIELDS)}",
        )

    # Get all collections user has access to (membership + ownership).
    if auth.user.is_admin:
        accessible_collections = db.scalars(select(Collection.id)).all()
    else:
        member_cids = set(
            db.scalars(
                select(CollectionMembership.collection_id).where(
                    CollectionMembership.user_id == auth.user.id
                )
            ).all()
        )
        owner_cids = set(
            db.scalars(select(Collection.id).where(Collection.owner_id == auth.user.id)).all()
        )
        accessible_collections = sorted(member_cids | owner_cids)

    if not accessible_collections:
        return []

    # Search across all accessible collections.
    stmt = (
        select(Item)
        .where(Item.collection_id.in_(accessible_collections))
        .options(selectinload(Item.photos))
    )
    if not include_archived:
        stmt = stmt.where(Item.archived_at.is_(None))

    items = db.scalars(stmt).all()
    if not items:
        return []

    item_ids = [item.id for item in items]
    doc_rows = db.execute(
        select(Document.item_id, Document.search_text)
        .where(Document.item_id.in_(item_ids))
        .where(Document.search_text.is_not(None))
    ).all()
    doc_text_by_item: dict[str, list[str]] = {}
    for item_id, search_text in doc_rows:
        if not search_text:
            continue
        doc_text_by_item.setdefault(item_id, []).append(search_text)

    # Category slug lookup (for `field=category` and `field=all`).
    cat_ids = {item.category_id for item in items if item.category_id}
    category_slug_by_id: dict[str, str] = {}
    if cat_ids:
        category_slug_by_id = dict(
            db.execute(select(Category.id, Category.slug).where(Category.id.in_(cat_ids))).all()
        )

    # Tag names per item (for `field=tag` and `field=all`).
    tag_names_by_item: dict[str, list[str]] = {}
    tag_rows = db.execute(
        select(ItemTag.item_id, Tag.name)
        .join(Tag, Tag.id == ItemTag.tag_id)
        .where(ItemTag.item_id.in_(item_ids))
    ).all()
    for it_id, tag_name in tag_rows:
        tag_names_by_item.setdefault(it_id, []).append(tag_name)

    # Normalize search term (accent-folding).
    normalized_q = unidecode(q.lower().strip())

    # Filter items using fuzzy matching with accent-folding.
    matched_items: list[tuple[Item, float]] = []

    for item in items:
        text = _item_field_text(
            item, field, doc_text_by_item, category_slug_by_id, tag_names_by_item
        )
        if not text:
            continue
        normalized_text = unidecode(text.lower())

        # Score: exact > substring.
        score = 0.0
        if normalized_q == normalized_text:
            score = 100.0
        elif normalized_q in normalized_text:
            score = 50.0 + (len(normalized_q) / max(len(normalized_text), 1)) * 50.0
        else:
            continue

        matched_items.append((item, score))

    # Sort by score descending, then by title
    matched_items.sort(key=lambda x: (-x[1], x[0].title or ""))

    # Compute rollups per collection for accurate values
    result = []
    by_collection: dict[str, list[tuple[Item, float]]] = {}
    for item, score in matched_items[:limit]:
        if item.collection_id not in by_collection:
            by_collection[item.collection_id] = []
        by_collection[item.collection_id].append((item, score))

    for collection_id, items_in_collection in by_collection.items():
        rollups = _compute_rollup_values(db, collection_id)
        for item, _ in items_in_collection:
            dto = _to_item_read(item, rollups)
            dto.tag_names = tag_names_by_item.get(item.id, [])
            result.append(dto)

    # Also search shopping list items (field=all only, unpurchased).
    if field == "all":
        shop_items = db.scalars(
            select(ShoppingItem)
            .where(ShoppingItem.collection_id.in_(accessible_collections))
            .where(ShoppingItem.purchased_at.is_(None))
        ).all()
        shop_matches: list[tuple[ShoppingItem, float]] = []
        for si in shop_items:
            text = " ".join(
                filter(None, [si.name or "", si.brand or "", si.notes or "", si.category_slug or ""])
            )
            if not text:
                continue
            norm_text = unidecode(text.lower())
            if normalized_q == norm_text:
                si_score = 100.0
            elif normalized_q in norm_text:
                si_score = 50.0 + (len(normalized_q) / max(len(norm_text), 1)) * 50.0
            else:
                continue
            shop_matches.append((si, si_score))
        shop_matches.sort(key=lambda x: (-x[1], x[0].name or ""))
        for si, _ in shop_matches:
            result.append(
                ItemRead(
                    id=si.id,
                    collection_id=si.collection_id,
                    category_id=None,
                    sort_order=0,
                    category_slug=si.category_slug,
                    title=si.name,
                    subtitle=si.brand,
                    notes=si.notes,
                    quantity=si.quantity,
                    wanted=si.list_type == "wish_list",
                    identifiers={},
                    attrs={},
                    depleted=False,
                    list_type=si.list_type,
                    created_at=si.created_at,
                    updated_at=si.updated_at,
                )
            )

    return result


@router.get("/grocery-list", response_model=list[ItemRead])
def grocery_list(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    """Return all depleted items across every collection the user can access.

    Any collection member can view this list — it forms the basis of a shared
    household grocery / re-stock list.
    """
    if auth.user.is_admin:
        stmt = (
            select(Item)
            .where(Item.depleted.is_(True))
            .options(selectinload(Item.photos))
            .order_by(Item.title)
        )
        return [ItemRead.model_validate(item) for item in db.scalars(stmt)]

    member_cids = set(
        db.scalars(
            select(CollectionMembership.collection_id).where(
                CollectionMembership.user_id == auth.user.id
            )
        ).all()
    )
    owner_cids = set(
        db.scalars(select(Collection.id).where(Collection.owner_id == auth.user.id)).all()
    )
    readable_cids = sorted(member_cids | owner_cids)
    if not readable_cids:
        return []

    stmt = (
        select(Item)
        .where(Item.collection_id.in_(readable_cids))
        .where(Item.archived_at.is_(None))
        .where(Item.depleted.is_(True))
        .options(selectinload(Item.photos))
        .order_by(Item.title)
    )
    return [ItemRead.model_validate(item) for item in db.scalars(stmt)]


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)
    data = payload.model_dump()
    cat_slug = data.pop("category", None)
    if not data.get("category_id"):
        if not cat_slug:
            # Fall back to the collection's default category when present —
            # lets quick-add flows (universal search empty-state, generic
            # wishlist add) succeed without forcing the user to pick a
            # category up front.
            col = db.get(Collection, payload.collection_id)
            if col is not None and col.default_category_slug:
                cat_slug = col.default_category_slug
        if not cat_slug:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either category_id or category (slug) is required",
            )
        try:
            data["category_id"] = resolve_slug(db, cat_slug).id
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
    elif db.get(Category, data["category_id"]) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown category_id"
        )
    if data.get("parent_id"):
        _validate_parent(db, data["parent_id"], payload.collection_id, child_id=None)
    if data.get("location_id"):
        _validate_location(db, data["location_id"], payload.collection_id)
    if data.get("template_id"):
        tmpl = db.get(ItemTemplate, data["template_id"])
        if tmpl is None or tmpl.collection_id != payload.collection_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown template",
            )
        data["attrs"] = validate_attrs(
            db,
            tmpl,
            data.get("attrs") or {},
            collection_id=payload.collection_id,
        )
    item = Item(**data)
    db.add(item)
    db.flush()
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.create",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={"title": item.title, "category_id": item.category_id},
    )
    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


@router.post("/bulk-patch", response_model=list[ItemRead])
def bulk_patch_items(
    payload: ItemBulkPatchRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)

    updates: dict[str, object] = {}
    if payload.depleted is not None:
        updates["depleted"] = payload.depleted
    if payload.wanted is not None:
        updates["wanted"] = payload.wanted
    if "location_id" in payload.model_fields_set:
        updates["location_id"] = payload.location_id
    if "category_id" in payload.model_fields_set or "category" in payload.model_fields_set:
        category_id = payload.category_id
        if not category_id and payload.category:
            try:
                category_id = resolve_slug(db, payload.category).id
            except LookupError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc
        if not category_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Either category_id or category (slug) is required for bulk move",
            )
        if db.get(Category, category_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown category_id",
            )
        updates["category_id"] = category_id
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one mutable field is required",
        )

    ids = list(dict.fromkeys(payload.item_ids))
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == payload.collection_id)
        .where(Item.id.in_(ids))
        .options(selectinload(Item.photos))
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more items not found in collection",
        )

    for item in rows:
        for key, value in updates.items():
            setattr(item, key, value)
        # Keep semantics aligned with single-item edits.
        item.flagged_note = None
        item.flagged_at = None

    db.commit()
    for item in rows:
        db.refresh(item)
    rollups = _compute_rollup_values(db, payload.collection_id)
    by_id = {item.id: item for item in rows}
    return [_to_item_read(by_id[item_id], rollups) for item_id in ids]


@router.post("/bulk-lend", response_model=list[LoanRead])
def bulk_lend_items(
    payload: ItemBulkLendRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[LoanRead]:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)

    ids = list(dict.fromkeys(payload.item_ids))
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == payload.collection_id)
        .where(Item.id.in_(ids))
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more items not found in collection",
        )
    if any(item.archived_at is not None for item in rows):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Archived items cannot be lent",
        )

    contact = db.get(Contact, payload.contact_id)
    if contact is None or contact.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    active_loan_item_ids = set(
        db.scalars(
            select(Loan.item_id)
            .where(Loan.item_id.in_(ids))
            .where(Loan.returned_at.is_(None))
        ).all()
    )
    if active_loan_item_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more items already have an active loan",
        )

    loaned_at = payload.loaned_at or datetime.now(UTC)
    notes = (payload.notes or "").strip() or None
    created: list[Loan] = []
    for item_id in ids:
        loan = Loan(
            item_id=item_id,
            contact_id=payload.contact_id,
            loaned_at=loaned_at,
            due_at=payload.due_at,
            notes=notes,
        )
        db.add(loan)
        created.append(loan)

    db.commit()
    for loan in created:
        db.refresh(loan)
    return [LoanRead.model_validate(loan) for loan in created]


@router.post("/bulk-delete", response_model=ItemBulkDeleteResponse)
def bulk_delete_items(
    payload: ItemBulkDeleteRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemBulkDeleteResponse:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)

    ids = list(dict.fromkeys(payload.item_ids))
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == payload.collection_id)
        .where(Item.id.in_(ids))
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more items not found in collection",
        )

    for item in rows:
        db.delete(item)
    db.commit()
    return ItemBulkDeleteResponse(deleted=len(rows))


@router.post("/bulk-archive", response_model=list[ItemRead])
def bulk_archive_items(
    payload: ItemBulkArchiveRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)

    ids = list(dict.fromkeys(payload.item_ids))
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == payload.collection_id)
        .where(Item.id.in_(ids))
        .options(selectinload(Item.photos))
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more items not found in collection",
        )

    archived_at = datetime.now(UTC)
    disposition_at = payload.disposition_at or archived_at
    disposition_buyer = (payload.disposition_buyer or "").strip() or None
    disposition_note = (payload.disposition_note or "").strip() or None
    for item in rows:
        item.archived_at = archived_at
        item.disposition_type = payload.disposition_type
        item.disposition_at = disposition_at
        item.disposition_amount = payload.disposition_amount
        item.disposition_buyer = disposition_buyer
        item.disposition_note = disposition_note
        item.wanted = False
        item.depleted = False

    db.commit()

    # Log audit entries for each archived item
    for item in rows:
        audit.log(
            db,
            actor_user_id=auth.user.id,
            action="item.archived",
            collection_id=payload.collection_id,
            target_type="item",
            target_id=item.id,
            payload={
                "title": item.title,
                "disposition_type": item.disposition_type,
                "disposition_amount": float(item.disposition_amount) if item.disposition_amount else None,
                "disposition_buyer": item.disposition_buyer,
                "bulk": True,
            },
        )

    db.commit()
    for item in rows:
        db.refresh(item)
    rollups = _compute_rollup_values(db, payload.collection_id)
    by_id = {item.id: item for item in rows}
    return [_to_item_read(by_id[item_id], rollups) for item_id in ids]


@router.post("/bulk-restore", response_model=list[ItemRead])
def bulk_restore_items(
    payload: ItemBulkRestoreRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)

    ids = list(dict.fromkeys(payload.item_ids))
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == payload.collection_id)
        .where(Item.id.in_(ids))
        .options(selectinload(Item.photos))
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more items not found in collection",
        )

    for item in rows:
        item.archived_at = None
        item.disposition_type = None
        item.disposition_at = None
        item.disposition_amount = None
        item.disposition_buyer = None
        item.disposition_note = None

    db.commit()

    # Log audit entries for each restored item
    for item in rows:
        audit.log(
            db,
            actor_user_id=auth.user.id,
            action="item.restored",
            collection_id=payload.collection_id,
            target_type="item",
            target_id=item.id,
            payload={"title": item.title, "bulk": True},
        )

    db.commit()
    for item in rows:
        db.refresh(item)
    rollups = _compute_rollup_values(db, payload.collection_id)
    by_id = {item.id: item for item in rows}
    return [_to_item_read(by_id[item_id], rollups) for item_id in ids]


@router.post("/bulk-tags", response_model=list[ItemRead])
def bulk_tag_items(
    payload: ItemBulkTagRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)

    ids = list(dict.fromkeys(payload.item_ids))
    tag_ids = list(dict.fromkeys(payload.tag_ids))
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == payload.collection_id)
        .where(Item.id.in_(ids))
        .options(selectinload(Item.photos))
    ).all()
    if len(rows) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more items not found in collection",
        )

    user_tags = db.scalars(
        select(Tag).where(Tag.owner_id == auth.user.id).where(Tag.id.in_(tag_ids))
    ).all()
    if len(user_tags) != len(tag_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more tags not found",
        )

    if payload.mode == "add":
        existing = {
            (item_id, tag_id)
            for item_id, tag_id in db.execute(
                select(ItemTag.item_id, ItemTag.tag_id)
                .where(ItemTag.item_id.in_(ids))
                .where(ItemTag.tag_id.in_(tag_ids))
            ).all()
        }
        for item_id in ids:
            for tag_id in tag_ids:
                if (item_id, tag_id) in existing:
                    continue
                db.add(ItemTag(item_id=item_id, tag_id=tag_id))
    else:
        db.execute(delete(ItemTag).where(ItemTag.item_id.in_(ids)).where(ItemTag.tag_id.in_(tag_ids)))

    db.commit()
    for item in rows:
        db.refresh(item)
    rollups = _compute_rollup_values(db, payload.collection_id)
    by_id = {item.id: item for item in rows}
    return [_to_item_read(by_id[item_id], rollups) for item_id in ids]


@router.get("/{item_id}", response_model=ItemRead)
def get_item(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rollups = _compute_rollup_values(db, item.collection_id)
    return _to_item_read(item, rollups)


@router.get("/{item_id}/tags", response_model=list[TagRead])
def list_item_tags(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[TagRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)

    rows = db.scalars(
        select(Tag)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .where(ItemTag.item_id == item_id)
        .where(Tag.owner_id == auth.user.id)
        .order_by(Tag.name)
    ).all()
    return [TagRead.model_validate(tag) for tag in rows]


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: str,
    payload: ItemUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates:
        slug = updates.pop("category")
        if slug:
            try:
                updates["category_id"] = resolve_slug(db, slug).id
            except LookupError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
                ) from exc
    if updates.get("category_id") and db.get(Category, updates["category_id"]) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown category_id"
        )
    if updates.get("parent_id"):
        _validate_parent(db, updates["parent_id"], item.collection_id, child_id=item.id)
    if updates.get("location_id"):
        _validate_location(db, updates["location_id"], item.collection_id)
    new_template_id = updates.get("template_id", item.template_id)
    if ("attrs" in updates or ("template_id" in updates and new_template_id)) and new_template_id:
        tmpl = db.get(ItemTemplate, new_template_id)
        if tmpl is None or tmpl.collection_id != item.collection_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unknown template",
            )
        base_attrs = updates.get("attrs") if "attrs" in updates else item.attrs
        updates["attrs"] = validate_attrs(
            db,
            tmpl,
            base_attrs or {},
            collection_id=item.collection_id,
        )

    # Any standard edit implicitly resolves the review flag.
    if updates:
        updates["flagged_note"] = None
        updates["flagged_at"] = None

    for key, value in updates.items():
        setattr(item, key, value)
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.update",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={"changes": list(updates.keys())},
    )
    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


@router.post("/{item_id}/flag", response_model=ItemRead)
def flag_item(
    item_id: str,
    payload: ItemFlagUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    note = (payload.note or "").strip()
    item.flagged_note = note or None
    item.flagged_at = datetime.now(UTC)
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.flag",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={"note": item.flagged_note},
    )
    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


@router.delete("/{item_id}/flag", response_model=ItemRead)
def unflag_item(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    item.flagged_note = None
    item.flagged_at = None
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.unflag",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload=None,
    )
    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


@router.post("/{item_id}/archive", response_model=ItemRead)
def archive_item(
    item_id: str,
    payload: ItemArchiveUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)

    item.archived_at = datetime.now(UTC)
    item.disposition_type = payload.disposition_type
    item.disposition_at = payload.disposition_at or datetime.now(UTC)
    item.disposition_amount = payload.disposition_amount
    item.disposition_buyer = (payload.disposition_buyer or "").strip() or None
    item.disposition_note = (payload.disposition_note or "").strip() or None
    # Archived items are not active wants/depleted state.
    item.wanted = False
    item.depleted = False

    # Log audit entry
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.archived",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={
            "title": item.title,
            "disposition_type": item.disposition_type,
            "disposition_amount": float(item.disposition_amount) if item.disposition_amount else None,
            "disposition_buyer": item.disposition_buyer,
        },
    )

    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


@router.post("/{item_id}/restore", response_model=ItemRead)
def restore_item(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)

    item.archived_at = None
    item.disposition_type = None
    item.disposition_at = None
    item.disposition_amount = None
    item.disposition_buyer = None
    item.disposition_note = None

    # Log audit entry
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.restored",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={"title": item.title},
    )

    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.delete",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={"title": item.title},
    )
    db.delete(item)
    db.commit()


@router.get("/{item_id}/children", response_model=list[ItemRead])
def list_item_children(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rollups = _compute_rollup_values(db, item.collection_id)
    rows = db.scalars(
        select(Item).where(Item.parent_id == item_id).order_by(Item.title)
    ).all()
    return [_to_item_read(r, rollups) for r in rows]


@router.get("/{item_id}/qr.png")
def item_qr_code(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> StreamingResponse:
    """Return a PNG QR code that encodes ``tangible://item/{item_id}``.

    Scanning this QR code with a Tangible-aware reader (or any URI-capable
    reader) identifies the item.  The caller must be a collection member.
    """
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)

    uri = f"tangible://item/{item_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


class QRLabelRequest(BaseModel):
    """Request to generate QR code labels."""

    collection_id: str
    item_ids: list[str]
    labels_per_row: int = 3


@router.post("/qr-labels/generate")
def generate_qr_labels(
    payload: QRLabelRequest,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> StreamingResponse:
    """Generate a PDF with QR code labels for selected items."""
    _require_role(db, auth, payload.collection_id, _VIEWER_ROLES)

    # Verify all item IDs belong to this collection
    items = db.scalars(
        select(Item).where(
            Item.id.in_(payload.item_ids),
            Item.collection_id == payload.collection_id,
        )
    ).all()

    if len(items) != len(payload.item_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Some items not found in this collection",
        )

    # Get collection name
    collection = db.get(Collection, payload.collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    # Prepare item data
    item_data = [{"id": item.id, "title": item.title or "Untitled"} for item in sorted(items, key=lambda i: i.title or "")]

    # Generate PDF
    pdf_bytes = generate_qr_codes_pdf(
        items=item_data,
        collection_name=collection.name,
        labels_per_row=payload.labels_per_row,
    )

    # Return as file download
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=qr-labels-{collection.name}.pdf"},
    )

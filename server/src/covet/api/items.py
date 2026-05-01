"""Item endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from covet.api.item_templates import validate_attrs
from covet.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from covet.db import get_session
from covet.models import Category, Collection, CollectionMembership, Item, ItemTemplate
from covet.schemas import (
    ItemArchiveUpdate,
    ItemBulkDeleteRequest,
    ItemBulkDeleteResponse,
    ItemBulkPatchRequest,
    ItemCreate,
    ItemFlagUpdate,
    ItemRead,
    ItemUpdate,
)
from covet.services.categories import resolve_slug, subtree_ids

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


def _apply_sort(
    stmt,
    *,
    sort_by: str,
    sort_dir: str,
    sort_attr: str | None,
):
    direction = asc if sort_dir == "asc" else desc

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
        detail="sort_by must be one of: title, value, acquired_at, attr",
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
        like = f"%{search.lower()}%"
        stmt = stmt.where(Item.title.ilike(like))
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
    if sort_dir not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort_dir must be one of: asc, desc",
        )
    stmt = stmt.options(selectinload(Item.photos))
    stmt = _apply_sort(stmt, sort_by=sort_by, sort_dir=sort_dir, sort_attr=sort_attr)
    stmt = stmt.limit(limit).offset(offset)
    return [_to_item_read(item, rollups) for item in db.scalars(stmt)]


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

    updates: dict[str, bool] = {}
    if payload.depleted is not None:
        updates["depleted"] = payload.depleted
    if payload.wanted is not None:
        updates["wanted"] = payload.wanted
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

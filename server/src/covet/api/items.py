"""Item endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from covet.api.item_templates import validate_attrs
from covet.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from covet.db import get_session
from covet.models import Category, CollectionMembership, Item, ItemTemplate
from covet.schemas import ItemCreate, ItemRead, ItemUpdate
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


@router.get("", response_model=list[ItemRead])
def list_items(
    collection_id: str = Query(...),
    category: str | None = Query(default=None, description="Category slug, e.g. 'music.vinyl'."),
    category_subtree: str | None = Query(
        default=None,
        description="Top-level category slug; matches the root and all of its children.",
    ),
    search: str | None = None,
    depleted: bool | None = Query(default=None, description="Filter by depleted status."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
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
    if depleted is not None:
        stmt = stmt.where(Item.depleted.is_(depleted))
    stmt = stmt.options(selectinload(Item.photos)).order_by(Item.title).limit(limit).offset(offset)
    return [ItemRead.model_validate(item) for item in db.scalars(stmt)]


@router.get("/grocery-list", response_model=list[ItemRead])
def grocery_list(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    """Return all depleted items across every collection the user can access.

    Any collection member can view this list — it forms the basis of a shared
    household grocery / re-stock list.
    """
    # Subquery: collection IDs accessible to this user.
    member_cids = db.scalars(
        select(CollectionMembership.collection_id).where(
            CollectionMembership.user_id == auth.user.id
        )
    ).all()
    if not member_cids:
        return []
    stmt = (
        select(Item)
        .where(Item.collection_id.in_(member_cids))
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
        data["attrs"] = validate_attrs(tmpl, data.get("attrs") or {})
    item = Item(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return ItemRead.model_validate(item)


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
    return ItemRead.model_validate(item)


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
        updates["attrs"] = validate_attrs(tmpl, base_attrs or {})
    for key, value in updates.items():
        setattr(item, key, value)
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
    rows = db.scalars(
        select(Item).where(Item.parent_id == item_id).order_by(Item.title)
    ).all()
    return [ItemRead.model_validate(r) for r in rows]

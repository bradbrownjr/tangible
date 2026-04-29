"""Item endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.api.item_templates import validate_attrs
from covet.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from covet.db import get_session
from covet.models import Item, ItemTemplate
from covet.models.item import ItemType
from covet.schemas import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("", response_model=list[ItemRead])
def list_items(
    collection_id: str = Query(...),
    type_filter: ItemType | None = Query(default=None, alias="type"),
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    stmt = select(Item).where(Item.collection_id == collection_id)
    if type_filter is not None:
        stmt = stmt.where(Item.type == type_filter)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(Item.title.ilike(like))
    stmt = stmt.order_by(Item.title).limit(limit).offset(offset)
    return [ItemRead.model_validate(item) for item in db.scalars(stmt)]


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemRead:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)
    data = payload.model_dump()
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

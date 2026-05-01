"""Location endpoints (collection-scoped hierarchical tree)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from covet.auth.deps import AuthContext, collection_role, require_user
from covet.db import get_session
from covet.models import Item, Location
from covet.schemas import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(prefix="/locations", tags=["locations"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _validate_parent_assignment(
    db: DBSession,
    *,
    location_id: str | None,
    parent_id: str | None,
    collection_id: str,
) -> None:
    if parent_id is None:
        return
    parent = db.get(Location, parent_id)
    if parent is None or parent.collection_id != collection_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parent location not found in this collection",
        )
    if location_id is not None and parent_id == location_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location cannot be its own parent",
        )
    seen: set[str] = set()
    cursor: Location | None = parent
    while cursor is not None:
        if cursor.id in seen or (location_id is not None and cursor.id == location_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parent assignment would create a cycle",
            )
        seen.add(cursor.id)
        cursor = cursor.parent


def _item_counts(db: DBSession, collection_id: str) -> dict[str, int]:
    rows = db.execute(
        select(Item.location_id, func.count(Item.id))
        .where(Item.collection_id == collection_id)
        .where(Item.location_id.is_not(None))
        .group_by(Item.location_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def _to_read(node: Location, counts: dict[str, int]) -> LocationRead:
    children = sorted(node.children, key=lambda n: n.name.casefold())
    return LocationRead(
        id=node.id,
        collection_id=node.collection_id,
        name=node.name,
        kind=node.kind,
        parent_id=node.parent_id,
        notes=node.notes,
        qr_slug=node.qr_slug,
        item_count=counts.get(node.id, 0),
        children=[_to_read(c, counts) for c in children],
    )


@router.get("", response_model=list[LocationRead])
def list_locations(
    collection_id: str = Query(..., description="Collection scope"),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[LocationRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    roots = db.scalars(
        select(Location)
        .where(Location.collection_id == collection_id)
        .where(Location.parent_id.is_(None))
        .options(selectinload(Location.children))
        .order_by(Location.name)
    ).unique().all()
    counts = _item_counts(db, collection_id)
    return [_to_read(r, counts) for r in sorted(roots, key=lambda n: n.name.casefold())]


@router.get("/{location_id}", response_model=LocationRead)
def get_location(
    location_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> LocationRead:
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, loc.collection_id, _VIEWER_ROLES)
    counts = _item_counts(db, loc.collection_id)
    return _to_read(loc, counts)


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> LocationRead:
    _require_role(db, auth, payload.collection_id, _EDITOR_ROLES)
    _validate_parent_assignment(
        db,
        location_id=None,
        parent_id=payload.parent_id,
        collection_id=payload.collection_id,
    )
    loc = Location(
        collection_id=payload.collection_id,
        name=payload.name,
        kind=payload.kind,
        parent_id=payload.parent_id,
        notes=payload.notes,
        qr_slug=payload.qr_slug,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    counts = _item_counts(db, loc.collection_id)
    return _to_read(loc, counts)


@router.patch("/{location_id}", response_model=LocationRead)
def update_location(
    location_id: str,
    payload: LocationUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> LocationRead:
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, loc.collection_id, _EDITOR_ROLES)
    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates and updates["parent_id"] != loc.parent_id:
        _validate_parent_assignment(
            db,
            location_id=loc.id,
            parent_id=updates["parent_id"],
            collection_id=loc.collection_id,
        )
    for key, value in updates.items():
        setattr(loc, key, value)
    db.commit()
    db.refresh(loc)
    counts = _item_counts(db, loc.collection_id)
    return _to_read(loc, counts)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    loc = db.get(Location, location_id)
    if loc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, loc.collection_id, _EDITOR_ROLES)
    db.delete(loc)
    db.commit()


def resolve_or_create(
    db: DBSession, *, collection_id: str, name: str | None
) -> str | None:
    """Resolve a free-text label to a Location id, creating one if needed.

    Used by importers and legacy backup payloads. The label becomes a top-level
    `room` node so legacy free-text labels remain usable. Empty/blank input
    returns ``None``.
    """
    if name is None:
        return None
    label = name.strip()
    if not label:
        return None
    existing = db.scalar(
        select(Location)
        .where(Location.collection_id == collection_id)
        .where(Location.parent_id.is_(None))
        .where(Location.name == label)
    )
    if existing is not None:
        return existing.id
    loc = Location(
        collection_id=collection_id,
        parent_id=None,
        name=label,
        kind="room",
    )
    db.add(loc)
    db.flush()
    return loc.id


def resolve_path_or_create(
    db: DBSession, *, collection_id: str, path: list[str]
) -> str | None:
    """Resolve a root-first list of names to a Location id, creating missing nodes.

    Each entry creates a `container` child under its parent if missing. The
    first entry is treated as a `room`.
    """
    parent_id: str | None = None
    last_id: str | None = None
    for index, raw in enumerate(path):
        name = (raw or "").strip()
        if not name:
            continue
        existing = db.scalar(
            select(Location)
            .where(Location.collection_id == collection_id)
            .where(Location.parent_id.is_(parent_id) if parent_id is None
                   else Location.parent_id == parent_id)
            .where(Location.name == name)
        )
        if existing is None:
            existing = Location(
                collection_id=collection_id,
                parent_id=parent_id,
                name=name,
                kind="room" if index == 0 else "container",
            )
            db.add(existing)
            db.flush()
        parent_id = existing.id
        last_id = existing.id
    return last_id

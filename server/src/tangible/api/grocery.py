"""Grocery list endpoints.

Combines two sources into a unified shopping feed per collection:

1. Ad-hoc ``GroceryItem`` rows added by household members.
2. ``Item`` rows where ``depleted=True`` (auto-suggested re-stocks).

Marking an entry purchased optionally restocks the linked pantry item
via the existing inventory flow.

Store/aisle endpoints let users map category slugs to physical store aisles
so the shopping feed can be sorted aisle-by-aisle on the client.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, collection_role, require_user
from tangible.db import get_session
from tangible.models import (
    Collection,
    GroceryItem,
    GroceryStore,
    GroceryStoreAisle,
    Item,
    ItemLot,
)
from tangible.models.user import CollectionMembership
from tangible.schemas import (
    GroceryAisleCreate,
    GroceryAisleRead,
    GroceryAisleUpdate,
    GroceryCount,
    GroceryFeedEntry,
    GroceryItemCreate,
    GroceryItemRead,
    GroceryItemUpdate,
    GroceryPurchaseRequest,
    GrocerySource,
    GroceryStoreCreate,
    GroceryStoreRead,
    GroceryStoreUpdate,
)
from tangible.services import audit

router = APIRouter(prefix="/grocery", tags=["grocery"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _readable_collection_ids(db: DBSession, auth: AuthContext) -> list[str]:
    if auth.user.is_admin:
        return list(db.scalars(select(Collection.id)).all())
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
    return sorted(member_cids | owner_cids)


def _require_role(db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _ad_hoc_to_feed(g: GroceryItem) -> GroceryFeedEntry:
    return GroceryFeedEntry(
        id=g.id,
        source=GrocerySource(kind="ad_hoc", item_id=g.linked_item_id),
        collection_id=g.collection_id,
        name=g.name,
        subtitle=None,
        quantity=g.quantity,
        unit=g.unit,
        notes=g.notes,
        category_slug=g.category_slug,
        linked_item_id=g.linked_item_id,
        purchased_at=g.purchased_at,
        created_at=g.created_at,
    )


def _depleted_to_feed(item: Item) -> GroceryFeedEntry:
    return GroceryFeedEntry(
        id=f"item:{item.id}",
        source=GrocerySource(kind="depleted_item", item_id=item.id),
        collection_id=item.collection_id,
        name=item.title,
        subtitle=item.subtitle,
        quantity=1,
        unit=None,
        notes=None,
        category_slug=item.category.slug if item.category else None,
        linked_item_id=item.id,
        purchased_at=None,
        created_at=item.updated_at,
    )


@router.get("", response_model=list[GroceryFeedEntry])
def list_grocery_feed(
    include_purchased: bool = Query(default=False),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[GroceryFeedEntry]:
    """Unified shopping feed across every collection the user can access."""
    cids = _readable_collection_ids(db, auth)
    if not cids:
        return []

    # Ad-hoc rows
    g_stmt = select(GroceryItem).where(GroceryItem.collection_id.in_(cids))
    if not include_purchased:
        g_stmt = g_stmt.where(GroceryItem.purchased_at.is_(None))
    g_stmt = g_stmt.order_by(GroceryItem.created_at.desc())
    ad_hoc = [_ad_hoc_to_feed(g) for g in db.scalars(g_stmt).all()]

    # Depleted items (skip those already linked from an open ad-hoc entry to
    # avoid double-listing the same restock target).
    open_linked = {
        gid
        for gid in db.scalars(
            select(GroceryItem.linked_item_id).where(
                GroceryItem.collection_id.in_(cids),
                GroceryItem.linked_item_id.is_not(None),
                GroceryItem.purchased_at.is_(None),
            )
        ).all()
        if gid
    }
    d_stmt = (
        select(Item)
        .where(Item.collection_id.in_(cids))
        .where(Item.archived_at.is_(None))
        .where(Item.depleted.is_(True))
        .order_by(Item.title)
    )
    depleted = [
        _depleted_to_feed(it)
        for it in db.scalars(d_stmt).all()
        if it.id not in open_linked
    ]

    return ad_hoc + depleted


@router.get("/count", response_model=GroceryCount)
def grocery_count(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryCount:
    """Lightweight count for the nav badge / conditional menu visibility."""
    cids = _readable_collection_ids(db, auth)
    if not cids:
        return GroceryCount(total=0, ad_hoc=0, depleted_items=0)

    open_linked = {
        gid
        for gid in db.scalars(
            select(GroceryItem.linked_item_id).where(
                GroceryItem.collection_id.in_(cids),
                GroceryItem.linked_item_id.is_not(None),
                GroceryItem.purchased_at.is_(None),
            )
        ).all()
        if gid
    }
    ad_hoc = int(
        db.scalar(
            select(func.count(GroceryItem.id)).where(
                GroceryItem.collection_id.in_(cids),
                GroceryItem.purchased_at.is_(None),
            )
        )
        or 0
    )
    depleted_ids = list(
        db.scalars(
            select(Item.id).where(
                Item.collection_id.in_(cids),
                Item.archived_at.is_(None),
                Item.depleted.is_(True),
            )
        ).all()
    )
    depleted = sum(1 for iid in depleted_ids if iid not in open_linked)
    return GroceryCount(total=ad_hoc + depleted, ad_hoc=ad_hoc, depleted_items=depleted)


@router.post("", response_model=GroceryItemRead, status_code=status.HTTP_201_CREATED)
def create_grocery_item(
    payload: GroceryItemCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryItemRead:
    _require_role(db, auth, payload.collection_id, _VIEWER_ROLES)
    if payload.linked_item_id is not None:
        item = db.get(Item, payload.linked_item_id)
        if item is None or item.collection_id != payload.collection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_item_id"
            )

    g = GroceryItem(
        collection_id=payload.collection_id,
        created_by_user_id=auth.user.id,
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        notes=payload.notes,
        linked_item_id=payload.linked_item_id,
    )
    db.add(g)
    db.flush()
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="grocery.create",
        collection_id=g.collection_id,
        target_type="grocery_item",
        target_id=g.id,
        payload={"name": g.name, "quantity": g.quantity, "linked_item_id": g.linked_item_id},
    )
    db.commit()
    db.refresh(g)
    return GroceryItemRead.model_validate(g)


@router.patch("/{grocery_id}", response_model=GroceryItemRead)
def update_grocery_item(
    grocery_id: str,
    payload: GroceryItemUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryItemRead:
    g = db.get(GroceryItem, grocery_id)
    if g is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, g.collection_id, _VIEWER_ROLES)

    data = payload.model_dump(exclude_unset=True)
    if "linked_item_id" in data and data["linked_item_id"] is not None:
        item = db.get(Item, data["linked_item_id"])
        if item is None or item.collection_id != g.collection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_item_id"
            )
    for k, v in data.items():
        setattr(g, k, v)

    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="grocery.update",
        collection_id=g.collection_id,
        target_type="grocery_item",
        target_id=g.id,
        payload={"changes": list(data.keys())},
    )
    db.commit()
    db.refresh(g)
    return GroceryItemRead.model_validate(g)


@router.delete("/{grocery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grocery_item(
    grocery_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    g = db.get(GroceryItem, grocery_id)
    if g is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, g.collection_id, _VIEWER_ROLES)
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="grocery.delete",
        collection_id=g.collection_id,
        target_type="grocery_item",
        target_id=g.id,
        payload={"name": g.name},
    )
    db.delete(g)
    db.commit()


@router.post("/{grocery_id}/purchase", response_model=GroceryItemRead)
def purchase_grocery_item(
    grocery_id: str,
    payload: GroceryPurchaseRequest | None = None,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryItemRead:
    """Mark an ad-hoc grocery entry purchased.

    When ``linked_item_id`` is set, also creates an ``ItemLot`` so the
    pantry quantity is restocked and ``depleted`` is cleared.
    """
    g = db.get(GroceryItem, grocery_id)
    if g is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, g.collection_id, _EDITOR_ROLES)
    if g.purchased_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Already purchased"
        )

    purchased_at = (payload.purchased_at if payload else None) or datetime.now(UTC)
    use_by_date = payload.use_by_date if payload else None

    g.purchased_at = purchased_at
    g.purchased_by_user_id = auth.user.id

    restocked_lot_id: str | None = None
    if g.linked_item_id is not None:
        item = db.get(Item, g.linked_item_id)
        if item is not None and item.collection_id == g.collection_id:
            lot = ItemLot(
                item_id=item.id,
                collection_id=item.collection_id,
                quantity=g.quantity,
                purchased_at=purchased_at,
                use_by_date=use_by_date,
            )
            db.add(lot)
            db.flush()
            # Recompute item.quantity / depleted from active lots.
            active = db.scalar(
                select(func.coalesce(func.sum(ItemLot.quantity), 0)).where(
                    ItemLot.item_id == item.id, ItemLot.is_active.is_(True)
                )
            )
            item.quantity = int(active or 0)
            item.depleted = False
            restocked_lot_id = lot.id

    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="grocery.purchase",
        collection_id=g.collection_id,
        target_type="grocery_item",
        target_id=g.id,
        payload={
            "linked_item_id": g.linked_item_id,
            "restocked_lot_id": restocked_lot_id,
            "quantity": g.quantity,
        },
    )
    db.commit()
    db.refresh(g)
    return GroceryItemRead.model_validate(g)


# ---------------------------------------------------------------------------
# Store + aisle management
# ---------------------------------------------------------------------------


def _own_store(db: DBSession, store_id: str, user_id: str) -> GroceryStore:
    store = db.get(GroceryStore, store_id)
    if store is None or store.owner_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.get("/stores", response_model=list[GroceryStoreRead])
def list_stores(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[GroceryStore]:
    """List all stores belonging to the current user."""
    return list(
        db.scalars(
            select(GroceryStore).where(GroceryStore.owner_user_id == auth.user.id)
        ).all()
    )


@router.post("/stores", response_model=GroceryStoreRead, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: GroceryStoreCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryStore:
    store = GroceryStore(owner_user_id=auth.user.id, name=payload.name)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.patch("/stores/{store_id}", response_model=GroceryStoreRead)
def update_store(
    store_id: str,
    payload: GroceryStoreUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryStore:
    store = _own_store(db, store_id, auth.user.id)
    if payload.name is not None:
        store.name = payload.name
    db.commit()
    db.refresh(store)
    return store


@router.delete("/stores/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store(
    store_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    store = _own_store(db, store_id, auth.user.id)
    db.delete(store)
    db.commit()


@router.get("/stores/{store_id}/aisles", response_model=list[GroceryAisleRead])
def list_aisles(
    store_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[GroceryStoreAisle]:
    store = _own_store(db, store_id, auth.user.id)
    return list(store.aisles)


@router.post(
    "/stores/{store_id}/aisles",
    response_model=GroceryAisleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_aisle(
    store_id: str,
    payload: GroceryAisleCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryStoreAisle:
    store = _own_store(db, store_id, auth.user.id)
    aisle = GroceryStoreAisle(store_id=store.id, name=payload.name, position=payload.position)
    aisle.category_slugs = payload.category_slugs
    db.add(aisle)
    db.commit()
    db.refresh(aisle)
    return aisle


@router.patch("/stores/{store_id}/aisles/{aisle_id}", response_model=GroceryAisleRead)
def update_aisle(
    store_id: str,
    aisle_id: str,
    payload: GroceryAisleUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> GroceryStoreAisle:
    _own_store(db, store_id, auth.user.id)
    aisle = db.get(GroceryStoreAisle, aisle_id)
    if aisle is None or aisle.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aisle not found")
    if payload.name is not None:
        aisle.name = payload.name
    if payload.position is not None:
        aisle.position = payload.position
    if payload.category_slugs is not None:
        aisle.category_slugs = payload.category_slugs
    db.commit()
    db.refresh(aisle)
    return aisle


@router.delete(
    "/stores/{store_id}/aisles/{aisle_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_aisle(
    store_id: str,
    aisle_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    _own_store(db, store_id, auth.user.id)
    aisle = db.get(GroceryStoreAisle, aisle_id)
    if aisle is None or aisle.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aisle not found")
    db.delete(aisle)
    db.commit()


@router.put("/stores/{store_id}/aisles/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_aisles(
    store_id: str,
    order: list[str],
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    """Set position of every aisle in one call. ``order`` is a list of aisle IDs
    in the desired sequence (0-indexed)."""
    store = _own_store(db, store_id, auth.user.id)
    aisle_map = {a.id: a for a in store.aisles}
    for pos, aisle_id in enumerate(order):
        if aisle_id in aisle_map:
            aisle_map[aisle_id].position = pos
    db.commit()


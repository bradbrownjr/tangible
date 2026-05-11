"""Shopping list endpoints.

Combines two sources into a unified shopping feed per collection:

1. Ad-hoc ``ShoppingItem`` rows added by household members.
2. ``Item`` rows where ``depleted=True`` (auto-suggested re-stocks).

Marking an entry purchased optionally restocks the linked pantry item
via the existing inventory flow.

Store/aisle endpoints let users map category slugs to physical store aisles
so the shopping feed can be sorted aisle-by-aisle on the client.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, collection_role, require_user
from tangible.db import get_session
from tangible.models import (
    Category,
    Collection,
    Item,
    ItemLot,
    ShoppingItem,
    ShoppingStore,
    ShoppingStoreAisle,
    UserListType,
)
from tangible.models.user import CollectionMembership
from tangible.schemas import (
    CollectionRead,
    PairCreate,
    PairRead,
    ShoppingAisleCreate,
    ShoppingAisleRead,
    ShoppingAisleUpdate,
    ShoppingCount,
    ShoppingFeedEntry,
    ShoppingItemCreate,
    ShoppingItemRead,
    ShoppingItemUpdate,
    ShoppingPurchaseRequest,
    ShoppingSource,
    ShoppingStoreCreate,
    ShoppingStoreRead,
    ShoppingStoreUpdate,
    UserListTypeCreate,
    UserListTypeRead,
    UserListTypeUpdate,
)
from tangible.api.item_templates import _do_scaffold
from tangible.services import audit
from tangible.services.categories import resolve_slug

router = APIRouter(prefix="/lists", tags=["shopping"])

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


def _ad_hoc_to_feed(g: ShoppingItem) -> ShoppingFeedEntry:
    return ShoppingFeedEntry(
        id=g.id,
        source=ShoppingSource(kind="ad_hoc", item_id=g.linked_item_id),
        collection_id=g.collection_id,
        name=g.name,
        subtitle=None,
        quantity=g.quantity,
        unit=g.unit,
        brand=g.brand,
        notes=g.notes,
        category_slug=g.category_slug,
        list_type=g.list_type,
        wish_url=g.wish_url,
        wish_priority=g.wish_priority,
        linked_item_id=g.linked_item_id,
        purchased_at=g.purchased_at,
        created_at=g.created_at,
    )


def _depleted_to_feed(item: Item, list_type: str = "groceries") -> ShoppingFeedEntry:
    return ShoppingFeedEntry(
        id=f"item:{item.id}",
        source=ShoppingSource(kind="depleted_item", item_id=item.id),
        collection_id=item.collection_id,
        name=item.title,
        subtitle=item.subtitle,
        quantity=1,
        unit=None,
        notes=None,
        category_slug=item.category.slug if item.category else None,
        list_type=list_type,
        linked_item_id=item.id,
        purchased_at=None,
        created_at=item.updated_at,
    )


@router.get("", response_model=list[ShoppingFeedEntry])
def list_shopping_feed(
    include_purchased: bool = Query(default=False),
    list_type: str | None = Query(default=None, description="Filter by list type: groceries|hardware|home_goods|wish_list"),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ShoppingFeedEntry]:
    """Unified shopping feed across every collection the user can access."""
    cids = _readable_collection_ids(db, auth)
    if not cids:
        return []

    # Ad-hoc rows
    g_stmt = select(ShoppingItem).where(ShoppingItem.collection_id.in_(cids))
    if not include_purchased:
        g_stmt = g_stmt.where(ShoppingItem.purchased_at.is_(None))
    if list_type is not None:
        g_stmt = g_stmt.where(ShoppingItem.list_type == list_type)
    g_stmt = g_stmt.order_by(ShoppingItem.created_at.desc())
    ad_hoc = [_ad_hoc_to_feed(g) for g in db.scalars(g_stmt).all()]

    # Depleted items from accessible collections.  When list_type is given,
    # only show depleted items for that type's backing collection (matched by
    # the list_type value stored on existing open ad-hoc entries, defaulting
    # to groceries when no type filter is specified).
    effective_type = list_type or "groceries"
    open_linked = {
        gid
        for gid in db.scalars(
            select(ShoppingItem.linked_item_id).where(
                ShoppingItem.collection_id.in_(cids),
                ShoppingItem.linked_item_id.is_not(None),
                ShoppingItem.purchased_at.is_(None),
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
        _depleted_to_feed(it, effective_type)
        for it in db.scalars(d_stmt).all()
        if it.id not in open_linked
    ]

    return ad_hoc + depleted


@router.get("/count", response_model=ShoppingCount)
def shopping_count(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingCount:
    """Lightweight count for the nav badge / conditional menu visibility."""
    cids = _readable_collection_ids(db, auth)
    if not cids:
        return ShoppingCount(total=0, ad_hoc=0, depleted_items=0, by_type={})

    open_linked = {
        gid
        for gid in db.scalars(
            select(ShoppingItem.linked_item_id).where(
                ShoppingItem.collection_id.in_(cids),
                ShoppingItem.linked_item_id.is_not(None),
                ShoppingItem.purchased_at.is_(None),
            )
        ).all()
        if gid
    }
    # Per-type ad-hoc counts
    rows = db.execute(
        select(ShoppingItem.list_type, func.count(ShoppingItem.id))
        .where(
            ShoppingItem.collection_id.in_(cids),
            ShoppingItem.purchased_at.is_(None),
        )
        .group_by(ShoppingItem.list_type)
    ).all()
    by_type: dict[str, int] = {lt: cnt for lt, cnt in rows}
    ad_hoc = sum(by_type.values())

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
    # Depleted items count toward groceries type in the by_type breakdown
    if depleted:
        by_type["groceries"] = by_type.get("groceries", 0) + depleted
    return ShoppingCount(total=ad_hoc + depleted, ad_hoc=ad_hoc, depleted_items=depleted, by_type=by_type)


# ---------------------------------------------------------------------------
# Custom user-defined list types
# ---------------------------------------------------------------------------


def _slugify(label: str) -> str:
    """Convert a human label to a safe slug (lowercase, underscores)."""
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s[:64] or "list"


def _unique_slug(db: DBSession, user_id: str, base_slug: str) -> str:
    """Return base_slug, or base_slug_2/3/... if already taken."""
    candidate = base_slug
    suffix = 2
    while db.scalar(
        select(UserListType).where(
            UserListType.user_id == user_id,
            UserListType.slug == candidate,
        )
    ) is not None:
        candidate = f"{base_slug}_{suffix}"
        suffix += 1
    return candidate


@router.post("/pairs", response_model=PairRead, status_code=status.HTTP_201_CREATED)
def create_pair(
    payload: PairCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> PairRead:
    """Atomically create a Collection + UserListType pair."""
    # 1. Create the collection
    collection = Collection(
        owner_id=auth.user.id,
        name=payload.label.strip(),
        description=payload.description,
        default_category_slug=payload.category_slug,
    )
    db.add(collection)
    db.flush()  # get collection.id without committing

    # 2. Scaffold item templates
    _do_scaffold(db, collection.id, payload.category_slug, auth.user.id)

    # 3. Create the list type with a unique slug
    slug = _unique_slug(db, auth.user.id, _slugify(payload.label))
    lt = UserListType(
        user_id=auth.user.id,
        slug=slug,
        label=payload.label.strip(),
        category_slug=payload.category_slug,
        linked_collection_id=collection.id,
    )
    db.add(lt)
    db.flush()  # get lt.id

    # 4. Link back
    collection.linked_list_type_slug = lt.slug
    db.commit()
    db.refresh(collection)
    db.refresh(lt)

    return PairRead(
        collection=CollectionRead.model_validate(collection),
        list_type=UserListTypeRead.model_validate(lt),
    )


@router.get("/types", response_model=list[UserListTypeRead])
def list_user_list_types(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[UserListTypeRead]:
    """Return all custom list types owned by the current user."""
    rows = db.scalars(
        select(UserListType)
        .where(UserListType.user_id == auth.user.id)
        .order_by(UserListType.sort_order, UserListType.created_at)
    ).all()
    return list(rows)


@router.post("/types", response_model=UserListTypeRead, status_code=status.HTTP_201_CREATED)
def create_user_list_type(
    payload: UserListTypeCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> UserListTypeRead:
    """Create a standalone custom list type (no paired collection)."""
    slug = _unique_slug(db, auth.user.id, _slugify(payload.label))
    lt = UserListType(
        user_id=auth.user.id,
        slug=slug,
        label=payload.label.strip(),
        icon=payload.icon,
        category_slug=payload.category_slug,
        linked_collection_id=payload.linked_collection_id,
    )
    db.add(lt)
    db.commit()
    db.refresh(lt)
    return lt


@router.patch("/types/{type_id}", response_model=UserListTypeRead)
def update_user_list_type(
    type_id: str,
    payload: UserListTypeUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> UserListTypeRead:
    lt = db.scalar(
        select(UserListType).where(
            UserListType.id == type_id,
            UserListType.user_id == auth.user.id,
        )
    )
    if lt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if payload.label is not None:
        lt.label = payload.label.strip()
    if payload.icon is not None:
        lt.icon = payload.icon
    if payload.sort_order is not None:
        lt.sort_order = payload.sort_order
    db.commit()
    db.refresh(lt)
    return lt


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_list_type(
    type_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    lt = db.scalar(
        select(UserListType).where(
            UserListType.id == type_id,
            UserListType.user_id == auth.user.id,
        )
    )
    if lt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(lt)
    db.commit()


@router.post("", response_model=ShoppingItemRead, status_code=status.HTTP_201_CREATED)
def create_shopping_item(
    payload: ShoppingItemCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingItemRead:
    _require_role(db, auth, payload.collection_id, _VIEWER_ROLES)
    if payload.linked_item_id is not None:
        item = db.get(Item, payload.linked_item_id)
        if item is None or item.collection_id != payload.collection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid linked_item_id"
            )

    g = ShoppingItem(
        collection_id=payload.collection_id,
        created_by_user_id=auth.user.id,
        name=payload.name,
        quantity=payload.quantity,
        unit=payload.unit,
        brand=payload.brand,
        notes=payload.notes,
        category_slug=payload.category_slug,
        list_type=payload.list_type,
        wish_url=payload.wish_url,
        wish_priority=payload.wish_priority,
        linked_item_id=payload.linked_item_id,
    )
    db.add(g)
    db.flush()
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="shopping.create",
        collection_id=g.collection_id,
        target_type="shopping_item",
        target_id=g.id,
        payload={"name": g.name, "quantity": g.quantity, "list_type": g.list_type, "linked_item_id": g.linked_item_id},
    )
    db.commit()
    db.refresh(g)
    return ShoppingItemRead.model_validate(g)


@router.patch("/{item_id}", response_model=ShoppingItemRead)
def update_shopping_item(
    item_id: str,
    payload: ShoppingItemUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingItemRead:
    g = db.get(ShoppingItem, item_id)
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
        action="shopping.update",
        collection_id=g.collection_id,
        target_type="shopping_item",
        target_id=g.id,
        payload={"changes": list(data.keys())},
    )
    db.commit()
    db.refresh(g)
    return ShoppingItemRead.model_validate(g)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_item(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    g = db.get(ShoppingItem, item_id)
    if g is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, g.collection_id, _VIEWER_ROLES)
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="shopping.delete",
        collection_id=g.collection_id,
        target_type="shopping_item",
        target_id=g.id,
        payload={"name": g.name},
    )
    db.delete(g)
    db.commit()


@router.post("/{item_id}/purchase", response_model=ShoppingItemRead)
def purchase_shopping_item(
    item_id: str,
    payload: ShoppingPurchaseRequest | None = None,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingItemRead:
    """Mark a shopping entry purchased (or gifted/received for wish lists).

    When ``linked_item_id`` is set, also creates an ``ItemLot`` so the
    backing collection quantity is restocked and ``depleted`` is cleared.
    """
    g = db.get(ShoppingItem, item_id)
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
    created_item_id: str | None = None
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
    else:
        # Ad-hoc shopping entry with no linked pantry/inventory item: create the
        # Item in the entry's collection so the purchase actually lands somewhere.
        # Resolve a category: prefer the entry's own slug, else the collection's
        # default. Category is optional now (nullable) so creation always happens.
        cat: Category | None = None
        if g.category_slug:
            try:
                cat = resolve_slug(db, g.category_slug)
            except LookupError:
                cat = None
        if cat is None:
            collection = db.get(Collection, g.collection_id)
            default_slug = collection.default_category_slug if collection is not None else None
            if default_slug:
                try:
                    cat = resolve_slug(db, default_slug)
                except LookupError:
                    cat = None
        new_item = Item(
            collection_id=g.collection_id,
            category_id=cat.id if cat is not None else None,
            title=g.name,
            quantity=g.quantity,
            notes=g.notes,
            attrs={"brand": g.brand} if g.brand else {},
        )
        db.add(new_item)
        db.flush()
        lot = ItemLot(
            item_id=new_item.id,
            collection_id=g.collection_id,
            quantity=g.quantity,
            purchased_at=purchased_at,
            use_by_date=use_by_date,
        )
        db.add(lot)
        db.flush()
        new_item.depleted = False
        new_item.quantity = g.quantity
        created_item_id = new_item.id
        restocked_lot_id = lot.id

    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="shopping.purchase",
        collection_id=g.collection_id,
        target_type="shopping_item",
        target_id=g.id,
        payload={
            "linked_item_id": g.linked_item_id,
            "restocked_lot_id": restocked_lot_id,
            "created_item_id": created_item_id,
            "quantity": g.quantity,
        },
    )
    db.commit()
    db.refresh(g)
    return ShoppingItemRead.model_validate(g)


# ---------------------------------------------------------------------------
# Store + aisle management
# ---------------------------------------------------------------------------


def _own_store(db: DBSession, store_id: str, user_id: str) -> ShoppingStore:
    store = db.get(ShoppingStore, store_id)
    if store is None or store.owner_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.get("/stores", response_model=list[ShoppingStoreRead])
def list_stores(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ShoppingStore]:
    """List all stores belonging to the current user."""
    return list(
        db.scalars(
            select(ShoppingStore).where(ShoppingStore.owner_user_id == auth.user.id)
        ).all()
    )


@router.post("/stores", response_model=ShoppingStoreRead, status_code=status.HTTP_201_CREATED)
def create_store(
    payload: ShoppingStoreCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingStore:
    store = ShoppingStore(owner_user_id=auth.user.id, name=payload.name)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.patch("/stores/{store_id}", response_model=ShoppingStoreRead)
def update_store(
    store_id: str,
    payload: ShoppingStoreUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingStore:
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


@router.get("/stores/{store_id}/aisles", response_model=list[ShoppingAisleRead])
def list_aisles(
    store_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ShoppingStoreAisle]:
    store = _own_store(db, store_id, auth.user.id)
    return list(store.aisles)


@router.post(
    "/stores/{store_id}/aisles",
    response_model=ShoppingAisleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_aisle(
    store_id: str,
    payload: ShoppingAisleCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingStoreAisle:
    store = _own_store(db, store_id, auth.user.id)
    aisle = ShoppingStoreAisle(store_id=store.id, name=payload.name, position=payload.position)
    aisle.category_slugs = payload.category_slugs
    db.add(aisle)
    db.commit()
    db.refresh(aisle)
    return aisle


@router.patch("/stores/{store_id}/aisles/{aisle_id}", response_model=ShoppingAisleRead)
def update_aisle(
    store_id: str,
    aisle_id: str,
    payload: ShoppingAisleUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ShoppingStoreAisle:
    _own_store(db, store_id, auth.user.id)
    aisle = db.get(ShoppingStoreAisle, aisle_id)
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
    aisle = db.get(ShoppingStoreAisle, aisle_id)
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


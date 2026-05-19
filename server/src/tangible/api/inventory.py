"""Inventory lots and alert endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, collection_role, require_user
from tangible.db import get_session
from tangible.models import Chore, Collection, Item, ItemLot, MaintenanceTask, StandaloneTask
from tangible.models.base import as_utc
from tangible.models.user import CollectionMembership
from tangible.schemas.inventory import (
    DueAlertRead,
    ItemLotCreate,
    ItemLotRead,
    ItemLotUpdate,
    RestockRequest,
)
from tangible.services import audit

router = APIRouter(tags=["inventory"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _sync_item_inventory_state(db: DBSession, item: Item) -> None:
    db.flush()
    active_units = db.scalar(
        select(func.coalesce(func.sum(ItemLot.quantity), 0)).where(
            ItemLot.item_id == item.id,
            ItemLot.is_active.is_(True),
        )
    )
    item.quantity = int(active_units or 0)
    item.depleted = item.quantity <= 0


@router.get("/items/{item_id}/lots", response_model=list[ItemLotRead])
def list_item_lots(
    item_id: str,
    include_inactive: bool = Query(default=True),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemLotRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)

    stmt = select(ItemLot).where(ItemLot.item_id == item_id)
    if not include_inactive:
        stmt = stmt.where(ItemLot.is_active.is_(True))
    stmt = stmt.order_by(ItemLot.use_by_date.is_(None), ItemLot.use_by_date, ItemLot.created_at)
    return [ItemLotRead.model_validate(row) for row in db.scalars(stmt).all()]


@router.post("/items/{item_id}/lots", response_model=ItemLotRead, status_code=status.HTTP_201_CREATED)
def create_item_lot(
    item_id: str,
    payload: ItemLotCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemLotRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)

    lot = ItemLot(item_id=item.id, collection_id=item.collection_id, **payload.model_dump())
    db.add(lot)
    _sync_item_inventory_state(db, item)
    db.commit()
    db.refresh(lot)
    return ItemLotRead.model_validate(lot)


@router.post("/items/{item_id}/restock", response_model=ItemLotRead, status_code=status.HTTP_201_CREATED)
def restock_item(
    item_id: str,
    payload: RestockRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemLotRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)

    # Idempotency: return the existing lot if the client is replaying a queued offline mutation.
    if idempotency_key:
        existing = db.scalar(select(ItemLot).where(ItemLot.idempotency_key == idempotency_key))
        if existing is not None:
            return ItemLotRead.model_validate(existing)

    lot = ItemLot(
        item_id=item.id,
        collection_id=item.collection_id,
        idempotency_key=idempotency_key,
        **payload.model_dump(exclude={"mark_in_stock"}),
    )
    db.add(lot)
    _sync_item_inventory_state(db, item)
    if payload.mark_in_stock:
        item.depleted = False
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="item.restock",
        collection_id=item.collection_id,
        target_type="item",
        target_id=item.id,
        payload={"lot_id": lot.id, "quantity": lot.quantity},
    )
    db.commit()
    db.refresh(lot)
    return ItemLotRead.model_validate(lot)


@router.patch("/lots/{lot_id}", response_model=ItemLotRead)
def update_lot(
    lot_id: str,
    payload: ItemLotUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemLotRead:
    lot = db.get(ItemLot, lot_id)
    if lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, lot.collection_id, _EDITOR_ROLES)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lot, key, value)

    item = db.get(Item, lot.item_id)
    assert item is not None
    _sync_item_inventory_state(db, item)
    db.commit()
    db.refresh(lot)
    return ItemLotRead.model_validate(lot)


@router.post("/lots/{lot_id}/consume", response_model=ItemLotRead)
def consume_lot(
    lot_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemLotRead:
    lot = db.get(ItemLot, lot_id)
    if lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, lot.collection_id, _EDITOR_ROLES)

    lot.is_active = False
    lot.consumed_at = datetime.now(UTC)

    item = db.get(Item, lot.item_id)
    assert item is not None
    _sync_item_inventory_state(db, item)
    db.commit()
    db.refresh(lot)
    return ItemLotRead.model_validate(lot)


@router.post("/lots/{lot_id}/freeze", response_model=ItemLotRead)
def freeze_lot(
    lot_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemLotRead:
    lot = db.get(ItemLot, lot_id)
    if lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, lot.collection_id, _EDITOR_ROLES)

    if lot.date_frozen is None:
        lot.date_frozen = datetime.now(UTC)
    db.commit()
    db.refresh(lot)
    return ItemLotRead.model_validate(lot)


@router.get("/alerts", response_model=list[DueAlertRead])
def list_alerts(
    within_days: int = Query(default=7, ge=0, le=3650),
    collection_id: str | None = Query(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[DueAlertRead]:
    if collection_id is not None:
        _require_role(db, auth, collection_id, _VIEWER_ROLES)
    return _build_alerts(auth=auth, db=db, within_days=within_days, collection_id=collection_id)  # type: ignore[return-value]


def _build_alerts(
    *,
    auth: AuthContext,
    db: DBSession,
    within_days: int,
    collection_id: str | None = None,
) -> list[DueAlertRead]:
    """Build and return alerts. Called by list_alerts and send_digest."""
    now = datetime.now(UTC)
    horizon = now + timedelta(days=within_days)

    owned_ids: set[str] = set(db.scalars(
        select(Collection.id).where(Collection.owner_id == auth.user.id)
    ).all())

    # Batch-load membership roles in one query to avoid N+1 collection_role() calls.
    membership_roles: dict[str, str] = dict(
        db.execute(
            select(CollectionMembership.collection_id, CollectionMembership.role)
            .where(CollectionMembership.user_id == auth.user.id)
        ).all()
    )

    readable_collection_ids = list(
        owned_ids
        | {
            cid for cid, role in membership_roles.items()
            if auth.user.is_admin or role in _VIEWER_ROLES
        }
    )

    if collection_id is not None:
        readable_collection_ids = [collection_id]

    if not readable_collection_ids:
        return []

    out: list[DueAlertRead] = []

    item_rows = db.execute(
        select(Item).where(
            Item.collection_id.in_(readable_collection_ids),
            Item.use_by_date.isnot(None),
            Item.use_by_date <= horizon,
        )
    ).scalars()
    for item in item_rows:
        due = as_utc(item.use_by_date)
        if due is None:
            continue
        out.append(
            DueAlertRead(
                id=f"item-useby-{item.id}",
                kind="item_use_by",
                severity="warning" if due >= now else "critical",
                title=f"Use soon: {item.title}",
                collection_id=item.collection_id,
                item_id=item.id,
                lot_id=None,
                due_at=due,
                details="Item-level use by date is approaching.",
            )
        )

    exp_rows = db.execute(
        select(Item).where(
            Item.collection_id.in_(readable_collection_ids),
            Item.expires_at.isnot(None),
            Item.expires_at <= horizon,
        )
    ).scalars()
    for item in exp_rows:
        due = as_utc(item.expires_at)
        if due is None:
            continue
        out.append(
            DueAlertRead(
                id=f"item-exp-{item.id}",
                kind="item_expires",
                severity="warning" if due >= now else "critical",
                title=f"Expiring: {item.title}",
                collection_id=item.collection_id,
                item_id=item.id,
                lot_id=None,
                due_at=due,
                details="Item expiration date is approaching.",
            )
        )

    lot_rows = db.execute(
        select(ItemLot, Item)
        .join(Item, Item.id == ItemLot.item_id)
        .where(
            ItemLot.collection_id.in_(readable_collection_ids),
            ItemLot.is_active.is_(True),
            ItemLot.use_by_date.isnot(None),
            ItemLot.use_by_date <= horizon,
        )
    ).all()
    for lot, item in lot_rows:
        due = as_utc(lot.use_by_date)
        if due is None:
            continue
        out.append(
            DueAlertRead(
                id=f"lot-useby-{lot.id}",
                kind="lot_use_by",
                severity="warning" if due >= now else "critical",
                title=f"Package due soon: {item.title}",
                collection_id=lot.collection_id,
                item_id=item.id,
                lot_id=lot.id,
                due_at=due,
                details=lot.label,
            )
        )

    task_rows = db.execute(
        select(MaintenanceTask, Item)
        .join(Item, Item.id == MaintenanceTask.item_id)
        .where(
            Item.collection_id.in_(readable_collection_ids),
            MaintenanceTask.next_due_at.isnot(None),
            MaintenanceTask.next_due_at <= horizon,
        )
    ).all()
    for task, item in task_rows:
        due = as_utc(task.next_due_at)
        if due is None:
            continue
        out.append(
            DueAlertRead(
                id=f"maintenance-{task.id}",
                kind="maintenance_due",
                severity="warning" if due >= now else "critical",
                title=f"Due: {task.name}",
                collection_id=item.collection_id,
                item_id=item.id,
                lot_id=None,
                due_at=due,
                details=item.title,
            )
        )

    chore_rows = db.execute(
        select(Chore)
        .where(
            Chore.next_due_at.isnot(None),
            Chore.next_due_at <= horizon,
            (
                Chore.collection_id.in_(readable_collection_ids)
                | (
                    Chore.collection_id.is_(None)
                    & (Chore.owner_user_id == auth.user.id)
                )
            ),
        )
    ).scalars()
    for chore in chore_rows:
        due = as_utc(chore.next_due_at)
        if due is None:
            continue
        out.append(
            DueAlertRead(
                id=f"chore-{chore.id}",
                kind="chore_due",
                severity="warning" if due >= now else "critical",
                title=f"Chore due: {chore.name}",
                collection_id=chore.collection_id,
                item_id=None,
                lot_id=None,
                due_at=due,
                details=chore.notes,
            )
        )

    # Standalone one-off tasks.
    task_rows = db.execute(
        select(StandaloneTask).where(
            StandaloneTask.collection_id.in_(readable_collection_ids),
            StandaloneTask.completed_at.is_(None),
            StandaloneTask.due_at.isnot(None),
            StandaloneTask.due_at <= horizon,
        )
    ).scalars()
    for task in task_rows:
        due = as_utc(task.due_at)
        if due is None:
            continue
        out.append(
            DueAlertRead(
                id=f"task-{task.id}",
                kind="task_due",
                severity="warning" if due >= now else "critical",
                title=task.title,
                collection_id=task.collection_id,
                item_id=task.item_id,
                lot_id=None,
                due_at=due,
                details=task.notes,
            )
        )

    # Low-stock: items where quantity < minimum_quantity.
    low_stock_rows = db.execute(
        select(Item).where(
            Item.collection_id.in_(readable_collection_ids),
            Item.minimum_quantity.isnot(None),
            Item.quantity < Item.minimum_quantity,
            Item.archived_at.is_(None),
        )
    ).scalars()
    for item in low_stock_rows:
        out.append(
            DueAlertRead(
                id=f"low-stock-{item.id}",
                kind="low_stock",
                severity="warning",
                title=f"Low stock: {item.title}",
                collection_id=item.collection_id,
                item_id=item.id,
                lot_id=None,
                due_at=None,
                details=f"Quantity {item.quantity} is below minimum {item.minimum_quantity}.",
            )
        )

    out.sort(key=lambda a: a.due_at or datetime.max.replace(tzinfo=UTC))
    return out

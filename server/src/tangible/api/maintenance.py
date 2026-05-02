"""Maintenance task endpoints."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, collection_role, require_user
from tangible.db import get_session
from tangible.models import Item, MaintenanceCompletion, MaintenanceTask, MaintenanceTaskConsumable
from tangible.schemas import (
    MaintenanceCompletePayload,
    MaintenanceCompletionRead,
    MaintenanceTaskCreate,
    MaintenanceTaskRead,
    MaintenanceTaskUpdate,
)

router = APIRouter(tags=["maintenance"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _compute_next_due(task: MaintenanceTask) -> None:
    """Populate ``next_due_at`` from interval + last_completed_at when needed."""
    if task.next_due_at is not None:
        return
    if task.interval_days is None:
        return
    base = task.last_completed_at or datetime.now(UTC)
    task.next_due_at = base + timedelta(days=task.interval_days)


@router.get("/items/{item_id}/maintenance", response_model=list[MaintenanceTaskRead])
def list_tasks(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[MaintenanceTaskRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(MaintenanceTask)
        .where(MaintenanceTask.item_id == item_id)
        .order_by(MaintenanceTask.next_due_at)
    ).all()
    return [MaintenanceTaskRead.model_validate(r) for r in rows]


@router.post(
    "/items/{item_id}/maintenance",
    response_model=MaintenanceTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    item_id: str,
    payload: MaintenanceTaskCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> MaintenanceTaskRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    task = MaintenanceTask(item_id=item_id, **payload.model_dump())
    _compute_next_due(task)
    db.add(task)
    db.commit()
    db.refresh(task)
    return MaintenanceTaskRead.model_validate(task)


@router.patch("/maintenance/{task_id}", response_model=MaintenanceTaskRead)
def update_task(
    task_id: str,
    payload: MaintenanceTaskUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> MaintenanceTaskRead:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return MaintenanceTaskRead.model_validate(task)


@router.post("/maintenance/{task_id}/complete", response_model=MaintenanceTaskRead)
def complete_task(
    task_id: str,
    payload: MaintenanceCompletePayload | None = Body(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> MaintenanceTaskRead:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    now = datetime.now(UTC)
    p = payload or MaintenanceCompletePayload()
    completion = MaintenanceCompletion(
        task_id=task_id,
        completed_at=now,
        **p.model_dump(),
    )
    db.add(completion)
    task.last_completed_at = now
    task.next_due_at = (
        now + timedelta(days=task.interval_days) if task.interval_days else None
    )
    # Auto-deplete linked consumable items.
    consumables = db.scalars(
        select(MaintenanceTaskConsumable).where(MaintenanceTaskConsumable.task_id == task_id)
    ).all()
    for tc in consumables:
        consumable = db.get(Item, tc.item_id)
        if consumable is not None:
            consumable.quantity = max(0, consumable.quantity - tc.depletion_quantity)
    db.commit()
    db.refresh(task)
    return MaintenanceTaskRead.model_validate(task)


@router.get(
    "/maintenance/{task_id}/history",
    response_model=list[MaintenanceCompletionRead],
)
def task_history(
    task_id: str,
    format: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[MaintenanceCompletionRead] | Response:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(MaintenanceCompletion)
        .where(MaintenanceCompletion.task_id == task_id)
        .order_by(MaintenanceCompletion.completed_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    completions = [MaintenanceCompletionRead.model_validate(r) for r in rows]

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "task_id", "completed_at", "notes", "cost", "currency",
            "technician", "odometer_reading", "hours_reading",
        ])
        for c in completions:
            writer.writerow([
                c.id, c.task_id, c.completed_at.isoformat(),
                c.notes or "", c.cost or "", c.currency or "",
                c.technician or "", c.odometer_reading or "", c.hours_reading or "",
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="task-{task_id}-history.csv"'},
        )
    return completions


@router.delete("/maintenance/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    db.delete(task)
    db.commit()


@router.get("/maintenance", response_model=list[MaintenanceTaskRead])
def list_due(
    within_days: int = Query(default=30, ge=0, le=3650),
    collection_id: str | None = Query(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[MaintenanceTaskRead]:
    """Tasks whose ``next_due_at`` is within the window, scoped to readable collections."""
    horizon = datetime.now(UTC) + timedelta(days=within_days)
    stmt = select(MaintenanceTask, Item).join(Item, Item.id == MaintenanceTask.item_id).where(
        MaintenanceTask.next_due_at.isnot(None),
        MaintenanceTask.next_due_at <= horizon,
    )
    if collection_id is not None:
        _require_role(db, auth, collection_id, _VIEWER_ROLES)
        stmt = stmt.where(Item.collection_id == collection_id)
    out: list[MaintenanceTaskRead] = []
    for task, item in db.execute(stmt).all():
        if collection_role(db, auth.user, item.collection_id) is None:
            continue
        out.append(MaintenanceTaskRead.model_validate(task))
    out.sort(key=lambda t: t.next_due_at or horizon)
    return out


class _ConsumableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    task_id: str
    item_id: str
    depletion_quantity: int


class _ConsumableAdd(BaseModel):
    item_id: str
    depletion_quantity: int = Field(default=1, ge=1)


@router.get("/maintenance/{task_id}/consumables", response_model=list[_ConsumableRead])
def list_consumables(
    task_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[_ConsumableRead]:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(MaintenanceTaskConsumable).where(MaintenanceTaskConsumable.task_id == task_id)
    ).all()
    return [_ConsumableRead.model_validate(r) for r in rows]


@router.post(
    "/maintenance/{task_id}/consumables",
    response_model=_ConsumableRead,
    status_code=status.HTTP_201_CREATED,
)
def add_consumable(
    task_id: str,
    payload: _ConsumableAdd,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> _ConsumableRead:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    consumable_item = db.get(Item, payload.item_id)
    if consumable_item is None or consumable_item.collection_id != item.collection_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Consumable item must be in the same collection",
        )
    link = MaintenanceTaskConsumable(
        task_id=task_id,
        item_id=payload.item_id,
        depletion_quantity=payload.depletion_quantity,
    )
    db.merge(link)
    db.commit()
    return _ConsumableRead.model_validate(link)


@router.delete("/maintenance/{task_id}/consumables/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_consumable(
    task_id: str,
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    task = db.get(MaintenanceTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, task.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    link = db.get(MaintenanceTaskConsumable, (task_id, item_id))
    if link is not None:
        db.delete(link)
        db.commit()


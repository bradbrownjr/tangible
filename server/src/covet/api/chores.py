"""Chores endpoints — recurring household tasks not tied to a specific item."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, collection_role, require_user
from covet.db import get_session
from covet.models import Chore, ChoreCompletion, Collection, Item
from covet.schemas import (
    ChoreCompletePayload,
    ChoreCompletionRead,
    ChoreCreate,
    ChoreRead,
    ChoreUpdate,
)
from covet.schemas.maintenance import QuickChorePayload

router = APIRouter(tags=["chores"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _compute_next_due(chore: Chore) -> None:
    if chore.next_due_at is not None:
        return
    if chore.interval_days is None:
        return
    base = chore.last_completed_at or datetime.now(UTC)
    chore.next_due_at = base + timedelta(days=chore.interval_days)


@router.get("/collections/{collection_id}/chores", response_model=list[ChoreRead])
def list_chores(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ChoreRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(Chore)
        .where(Chore.collection_id == collection_id)
        .order_by(Chore.next_due_at.nullslast())
    ).all()
    return [ChoreRead.model_validate(r) for r in rows]


@router.post(
    "/collections/{collection_id}/chores",
    response_model=ChoreRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chore(
    collection_id: str,
    payload: ChoreCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ChoreRead:
    _require_role(db, auth, collection_id, _EDITOR_ROLES)
    if db.get(Collection, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    chore = Chore(collection_id=collection_id, **payload.model_dump())
    _compute_next_due(chore)
    db.add(chore)
    db.commit()
    db.refresh(chore)
    return ChoreRead.model_validate(chore)


@router.get("/chores/{chore_id}", response_model=ChoreRead)
def get_chore(
    chore_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ChoreRead:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, chore.collection_id, _VIEWER_ROLES)
    return ChoreRead.model_validate(chore)


@router.patch("/chores/{chore_id}", response_model=ChoreRead)
def update_chore(
    chore_id: str,
    payload: ChoreUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ChoreRead:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, chore.collection_id, _EDITOR_ROLES)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(chore, k, v)
    db.commit()
    db.refresh(chore)
    return ChoreRead.model_validate(chore)


@router.delete("/chores/{chore_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chore(
    chore_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, chore.collection_id, _EDITOR_ROLES)
    db.delete(chore)
    db.commit()


@router.post("/chores/{chore_id}/complete", response_model=ChoreRead)
def complete_chore(
    chore_id: str,
    payload: ChoreCompletePayload | None = Body(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ChoreRead:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, chore.collection_id, _EDITOR_ROLES)
    now = datetime.now(UTC)
    p = payload or ChoreCompletePayload()
    completion = ChoreCompletion(
        chore_id=chore_id,
        completed_at=now,
        **p.model_dump(),
    )
    db.add(completion)
    chore.last_completed_at = now
    chore.next_due_at = (
        now + timedelta(days=chore.interval_days) if chore.interval_days else None
    )
    db.commit()
    db.refresh(chore)
    return ChoreRead.model_validate(chore)


@router.get(
    "/chores/{chore_id}/history",
    response_model=list[ChoreCompletionRead],
)
def chore_history(
    chore_id: str,
    format: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ChoreCompletionRead] | Response:
    chore = db.get(Chore, chore_id)
    if chore is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, chore.collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(ChoreCompletion)
        .where(ChoreCompletion.chore_id == chore_id)
        .order_by(ChoreCompletion.completed_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    completions = [ChoreCompletionRead.model_validate(r) for r in rows]

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "chore_id", "completed_at", "notes", "cost", "currency", "technician"])
        for c in completions:
            writer.writerow([
                c.id, c.chore_id, c.completed_at.isoformat(),
                c.notes or "", c.cost or "", c.currency or "", c.technician or "",
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="chore-{chore_id}-history.csv"'},
        )
    return completions


@router.post("/items/{item_id}/quick-chore", response_model=ChoreRead, status_code=status.HTTP_200_OK)
def quick_chore(
    item_id: str,
    payload: QuickChorePayload,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ChoreRead:
    """Find-or-create a named chore for this item's collection and complete it immediately.

    If a chore with the given name already exists in the collection it is reused.
    If it doesn't exist, one is created with the supplied interval_days.
    Either way the chore is marked complete right now.
    """
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)

    chore = db.scalars(
        select(Chore).where(
            Chore.collection_id == item.collection_id,
            Chore.name == payload.chore_name,
        )
    ).first()

    now = datetime.now(UTC)

    if chore is None:
        chore = Chore(
            collection_id=item.collection_id,
            name=payload.chore_name,
            interval_days=payload.interval_days,
            last_completed_at=now,
            next_due_at=(now + timedelta(days=payload.interval_days)) if payload.interval_days else None,
        )
        db.add(chore)
        db.flush()
    else:
        if payload.interval_days is not None and chore.interval_days is None:
            chore.interval_days = payload.interval_days
        chore.last_completed_at = now
        chore.next_due_at = (
            now + timedelta(days=chore.interval_days) if chore.interval_days else None
        )

    completion = ChoreCompletion(
        chore_id=chore.id,
        completed_at=now,
        notes=payload.notes,
        cost=payload.cost,
        currency=payload.currency,
        technician=payload.technician,
    )
    db.add(completion)
    db.commit()
    db.refresh(chore)
    return ChoreRead.model_validate(chore)

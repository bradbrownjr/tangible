"""Category catalog endpoints (read-only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, require_user
from covet.db import get_session
from covet.models import Category
from covet.schemas import CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[CategoryRead]:
    rows = db.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(
            Category.parent_id.is_(None).desc(),
            Category.position,
            Category.name,
        )
    ).all()
    return [CategoryRead.model_validate(c) for c in rows]


@router.get("/tree")
def category_tree(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(
            Category.position, Category.name
        )
    ).all()
    by_parent: dict[str | None, list[Category]] = {}
    for c in rows:
        by_parent.setdefault(c.parent_id, []).append(c)

    def build(parent_id: str | None) -> list[dict[str, Any]]:
        return [
            {
                "id": c.id,
                "slug": c.slug,
                "name": c.name,
                "description": c.description,
                "children": build(c.id),
            }
            for c in by_parent.get(parent_id, [])
        ]

    return build(None)

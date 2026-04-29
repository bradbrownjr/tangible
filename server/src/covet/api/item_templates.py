"""ItemTemplate endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from covet.db import get_session
from covet.models import ItemTemplate
from covet.schemas import (
    ItemTemplateCreate,
    ItemTemplateRead,
    ItemTemplateUpdate,
    TemplateField,
)

router = APIRouter(tags=["item-templates"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get(
    "/collections/{collection_id}/templates",
    response_model=list[ItemTemplateRead],
)
def list_templates(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemTemplateRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(ItemTemplate)
        .where(ItemTemplate.collection_id == collection_id)
        .order_by(ItemTemplate.name)
    ).all()
    return [ItemTemplateRead.model_validate(r) for r in rows]


@router.post(
    "/collections/{collection_id}/templates",
    response_model=ItemTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    collection_id: str,
    payload: ItemTemplateCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    _require_role(db, auth, collection_id, _EDITOR_ROLES)
    tmpl = ItemTemplate(
        collection_id=collection_id,
        name=payload.name,
        item_type=payload.item_type,
        description=payload.description,
        fields=[f.model_dump() for f in payload.fields],
        created_by=auth.user.id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return ItemTemplateRead.model_validate(tmpl)


@router.get("/templates/{template_id}", response_model=ItemTemplateRead)
def get_template(
    template_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _VIEWER_ROLES)
    return ItemTemplateRead.model_validate(tmpl)


@router.patch("/templates/{template_id}", response_model=ItemTemplateRead)
def update_template(
    template_id: str,
    payload: ItemTemplateUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _EDITOR_ROLES)
    data = payload.model_dump(exclude_unset=True)
    if "fields" in data and data["fields"] is not None:
        data["fields"] = [f if isinstance(f, dict) else f.model_dump() for f in data["fields"]]
    for k, v in data.items():
        setattr(tmpl, k, v)
    db.commit()
    db.refresh(tmpl)
    return ItemTemplateRead.model_validate(tmpl)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _EDITOR_ROLES)
    db.delete(tmpl)
    db.commit()


# ---------------------------------------------------------------------------
# Validation helpers (used by items API)
# ---------------------------------------------------------------------------


def validate_attrs(template: ItemTemplate, attrs: dict[str, Any]) -> dict[str, Any]:
    """Validate ``attrs`` against ``template.fields``.

    Returns the (possibly coerced) attrs dict; raises HTTPException on error.
    Unknown keys are preserved as-is so callers can carry forward legacy data.
    """
    out: dict[str, Any] = dict(attrs)
    field_specs: list[TemplateField] = [TemplateField.model_validate(f) for f in template.fields]
    for spec in field_specs:
        value = out.get(spec.key)
        if value is None or value == "":
            if spec.required:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Field '{spec.key}' is required",
                )
            if spec.default is not None and spec.key not in out:
                out[spec.key] = spec.default
            continue
        out[spec.key] = _coerce(spec, value)
    return out


def _coerce(spec: TemplateField, value: Any) -> Any:
    t = spec.type
    try:
        if t == "text" or t == "url":
            return str(value)
        if t == "number":
            return float(value)
        if t == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if t == "date":
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)
        if t == "select":
            sval = str(value)
            if spec.options and sval not in spec.options:
                raise ValueError(
                    f"value '{sval}' not in allowed options for '{spec.key}'"
                )
            return sval
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Field '{spec.key}': {exc}",
        ) from exc
    return value

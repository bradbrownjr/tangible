"""Share-link management and public read-only collection views."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, require_collection_role
from covet.db import get_session
from covet.models import Collection, Item, ShareLink
from covet.schemas import (
    CollectionRead,
    ItemRead,
    ShareLinkCreate,
    ShareLinkRead,
)
from covet.services import audit

router = APIRouter(tags=["share"])


def _generate_slug() -> str:
    return secrets.token_urlsafe(16)


@router.get(
    "/collections/{collection_id}/share-links",
    response_model=list[ShareLinkRead],
)
def list_share_links(
    collection_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> list[ShareLink]:
    rows = db.scalars(
        select(ShareLink)
        .where(ShareLink.collection_id == collection_id)
        .order_by(ShareLink.created_at.desc())
    ).all()
    return list(rows)


@router.post(
    "/collections/{collection_id}/share-links",
    response_model=ShareLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_share_link(
    collection_id: str,
    payload: ShareLinkCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_collection_role("owner")),
) -> ShareLink:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    link = ShareLink(
        collection_id=collection_id,
        slug=_generate_slug(),
        label=payload.label,
        expires_at=payload.expires_at,
        revoked=False,
    )
    db.add(link)
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="share_link.create",
        collection_id=collection_id,
        target_type="share_link",
        target_id=link.id,
        payload={"label": payload.label},
    )
    db.commit()
    db.refresh(link)
    return link


@router.delete(
    "/collections/{collection_id}/share-links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_share_link(
    collection_id: str,
    link_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_collection_role("owner")),
) -> None:
    link = db.get(ShareLink, link_id)
    if link is None or link.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="share_link.revoke",
        collection_id=collection_id,
        target_type="share_link",
        target_id=link.id,
    )
    db.delete(link)
    db.commit()


# --- Public (no auth) ----------------------------------------------------------------------


def _resolve_share(db: DBSession, slug: str) -> ShareLink:
    link = db.scalar(select(ShareLink).where(ShareLink.slug == slug))
    if link is None or link.revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")
    return link


@router.get("/public/share/{slug}", response_model=CollectionRead)
def public_share_collection(
    slug: str,
    db: DBSession = Depends(get_session),
) -> CollectionRead:
    link = _resolve_share(db, slug)
    collection = db.get(Collection, link.collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return CollectionRead.model_validate(collection)


@router.get("/public/share/{slug}/items", response_model=list[ItemRead])
def public_share_items(
    slug: str,
    db: DBSession = Depends(get_session),
) -> list[Item]:
    link = _resolve_share(db, slug)
    rows = db.scalars(
        select(Item)
        .where(Item.collection_id == link.collection_id)
        .order_by(Item.title)
    ).all()
    return list(rows)

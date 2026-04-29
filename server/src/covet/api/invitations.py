"""Invitation lifecycle: create, list, revoke, preview, accept."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, require_collection_role, require_user
from covet.db import get_session
from covet.models import Collection, CollectionMembership, Invitation
from covet.schemas import (
    InvitationCreate,
    InvitationCreated,
    InvitationPreview,
    InvitationRead,
)

router = APIRouter(tags=["invitations"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def _is_active(inv: Invitation) -> bool:
    if inv.accepted_at is not None:
        return False
    expires = _normalize(inv.expires_at)
    return expires is None or expires >= datetime.now(UTC)


@router.get(
    "/collections/{collection_id}/invitations",
    response_model=list[InvitationRead],
)
def list_invitations(
    collection_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> list[Invitation]:
    rows = db.scalars(
        select(Invitation)
        .where(Invitation.collection_id == collection_id)
        .order_by(Invitation.created_at.desc())
    ).all()
    return list(rows)


@router.post(
    "/collections/{collection_id}/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    collection_id: str,
    payload: InvitationCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_collection_role("owner")),
) -> InvitationCreated:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    token = secrets.token_urlsafe(32)
    inv = Invitation(
        collection_id=collection_id,
        role=payload.role,
        token_hash=_hash_token(token),
        email=payload.email,
        expires_at=payload.expires_at,
        created_by=auth.user.id,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return InvitationCreated(
        id=inv.id,
        collection_id=inv.collection_id,
        role=inv.role,
        email=inv.email,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        created_at=inv.created_at,
        token=token,
    )


@router.delete(
    "/collections/{collection_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_invitation(
    collection_id: str,
    invitation_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> None:
    inv = db.get(Invitation, invitation_id)
    if inv is None or inv.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(inv)
    db.commit()


def _resolve_invitation(db: DBSession, token: str) -> Invitation:
    inv = db.scalar(
        select(Invitation).where(Invitation.token_hash == _hash_token(token))
    )
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not _is_active(inv):
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Invitation no longer valid"
        )
    return inv


@router.get("/invitations/{token}", response_model=InvitationPreview)
def preview_invitation(
    token: str, db: DBSession = Depends(get_session)
) -> InvitationPreview:
    inv = _resolve_invitation(db, token)
    collection = db.get(Collection, inv.collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return InvitationPreview(
        collection_id=collection.id,
        collection_name=collection.name,
        role=inv.role,
        email=inv.email,
        expires_at=inv.expires_at,
    )


@router.post(
    "/invitations/{token}/accept",
    status_code=status.HTTP_204_NO_CONTENT,
)
def accept_invitation(
    token: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    inv = _resolve_invitation(db, token)
    collection = db.get(Collection, inv.collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    user = auth.user
    if user.id == collection.owner_id:
        # Owner doesn't need a membership row; just consume the invite.
        inv.accepted_at = datetime.now(UTC)
        db.commit()
        return

    existing = db.scalar(
        select(CollectionMembership).where(
            CollectionMembership.collection_id == collection.id,
            CollectionMembership.user_id == user.id,
        )
    )
    if existing is None:
        db.add(
            CollectionMembership(
                collection_id=collection.id,
                user_id=user.id,
                role=inv.role,
            )
        )
    else:
        # Don't downgrade an existing higher role.
        rank = {"viewer": 0, "editor": 1, "owner": 2}
        if rank[inv.role] > rank.get(existing.role, 0):
            existing.role = inv.role

    inv.accepted_at = datetime.now(UTC)
    db.commit()

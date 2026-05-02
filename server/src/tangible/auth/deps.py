"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.service import api_token_user, session_for_token
from tangible.config import Settings, get_settings
from tangible.db import get_session
from tangible.models import Collection, CollectionMembership, User


@dataclass
class AuthContext:
    user: User
    via: str  # "session" | "token"


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip() or None
    return None


def get_current_user(
    request: Request,
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthContext | None:
    """Return the authenticated user, if any. Does not raise on failure."""
    cookie = request.cookies.get(settings.session_cookie_name)
    if cookie:
        sess = session_for_token(db, raw_token=cookie)
        if sess is not None:
            user = db.get(User, sess.user_id)
            if user is not None and user.is_active:
                return AuthContext(user=user, via="session")

    token = _bearer_token(request)
    if token:
        user = api_token_user(db, raw_token=token)
        if user is not None and user.is_active:
            return AuthContext(user=user, via="token")
    return None


def require_user(
    auth: AuthContext | None = Depends(get_current_user),
) -> AuthContext:
    if auth is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return auth


def require_admin(
    auth: AuthContext = Depends(require_user),
) -> AuthContext:
    if not auth.user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return auth


def collection_role(
    db: DBSession, user: User, collection_id: str
) -> str | None:
    collection = db.get(Collection, collection_id)
    if collection is None:
        return None
    if collection.owner_id == user.id or user.is_admin:
        return "owner"
    membership = db.scalar(
        select(CollectionMembership).where(
            CollectionMembership.collection_id == collection_id,
            CollectionMembership.user_id == user.id,
        )
    )
    return membership.role if membership else None


_ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2}


def require_collection_role(min_role: str):
    """Dependency factory that enforces a minimum role on ``collection_id`` path param."""
    if min_role not in _ROLE_RANK:
        raise ValueError(f"Unknown role: {min_role}")

    def _dep(
        collection_id: str,
        auth: AuthContext = Depends(require_user),
        db: DBSession = Depends(get_session),
    ) -> AuthContext:
        role = collection_role(db, auth.user, collection_id)
        if role is None or _ROLE_RANK[role] < _ROLE_RANK[min_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role >= {min_role} on this collection",
            )
        return auth

    return _dep

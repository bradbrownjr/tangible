"""Authentication & session services."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.config import Settings
from tangible.models import APIToken, Session, User
from tangible.models.base import as_utc, utcnow
from tangible.security import generate_token, hash_password, verify_password


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(
    db: DBSession,
    *,
    username: str,
    password: str | None,
    email: str | None = None,
    display_name: str | None = None,
    is_admin: bool = False,
) -> User:
    user = User(
        username=username,
        email=email,
        display_name=display_name,
        password_hash=hash_password(password) if password else None,
        is_admin=is_admin,
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: DBSession, *, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = utcnow()
    db.flush()
    return user


def create_session(
    db: DBSession,
    *,
    user: User,
    settings: Settings,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[Session, str]:
    raw = generate_token()
    session = Session(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    db.flush()
    return session, raw


def revoke_session(db: DBSession, *, raw_token: str) -> None:
    session = db.scalar(select(Session).where(Session.token_hash == _hash_token(raw_token)))
    if session is not None:
        session.revoked = True
        db.flush()


def session_for_token(db: DBSession, *, raw_token: str) -> Session | None:
    session = db.scalar(select(Session).where(Session.token_hash == _hash_token(raw_token)))
    if session is None or session.revoked:
        return None
    if as_utc(session.expires_at) < utcnow():
        return None
    return session


def create_api_token(
    db: DBSession,
    *,
    user: User,
    name: str,
    ttl_days: int = 0,
) -> tuple[APIToken, str]:
    raw = generate_token()
    expires_at = None
    if ttl_days > 0:
        expires_at = utcnow() + timedelta(days=ttl_days)
    token = APIToken(
        user_id=user.id,
        name=name,
        token_hash=_hash_token(raw),
        expires_at=expires_at,
    )
    db.add(token)
    db.flush()
    return token, raw


def api_token_user(db: DBSession, *, raw_token: str) -> User | None:
    token = db.scalar(select(APIToken).where(APIToken.token_hash == _hash_token(raw_token)))
    if token is None or token.revoked:
        return None
    if token.expires_at is not None and as_utc(token.expires_at) < utcnow():
        return None
    token.last_used_at = utcnow()
    db.flush()
    return db.get(User, token.user_id)

"""OIDC client + user upsert.

Wraps Authlib's async OAuth client. One :class:`authlib.OAuth` instance is
held in module state so providers' JWKS caches stay warm across requests.
Provider configs come from :attr:`Settings.oidc_providers`.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.service import create_user
from tangible.config import OIDCProvider, Settings
from tangible.models import OIDCIdentity, User

_oauth: OAuth | None = None
_registered: set[str] = set()


def _registry() -> OAuth:
    global _oauth
    if _oauth is None:
        _oauth = OAuth()
    return _oauth


def reset_registry() -> None:
    """Drop the cached registry (used by tests)."""
    global _oauth
    _oauth = None
    _registered.clear()


def get_provider(settings: Settings, name: str) -> OIDCProvider | None:
    for p in settings.oidc_providers:
        if p.name == name:
            return p
    return None


def client_for(settings: Settings, name: str) -> StarletteOAuth2App | None:
    """Return a registered Authlib OAuth client for the named provider."""
    provider = get_provider(settings, name)
    if provider is None:
        return None
    registry = _registry()
    if name not in _registered:
        registry.register(
            name=provider.name,
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            server_metadata_url=f"{provider.issuer.rstrip('/')}/.well-known/openid-configuration",
            client_kwargs={"scope": provider.scopes},
        )
        _registered.add(name)
    return registry.create_client(name)  # type: ignore[return-value]


def _make_username(claims: dict[str, Any], provider: OIDCProvider) -> str:
    raw = (
        claims.get(provider.username_claim)
        or claims.get("preferred_username")
        or claims.get("email")
        or claims.get("sub")
        or secrets.token_hex(8)
    )
    return str(raw)[:64]


def upsert_user_from_claims(
    db: DBSession,
    *,
    settings: Settings,
    provider: OIDCProvider,
    claims: dict[str, Any],
) -> User | None:
    """Find-or-create a User from ID-token claims.

    Returns the user, or None if the provider didn't supply a subject and we
    can't safely link.
    """
    subject = claims.get("sub")
    if not subject:
        return None
    subject = str(subject)

    identity = db.scalar(
        select(OIDCIdentity).where(
            OIDCIdentity.provider == provider.name,
            OIDCIdentity.subject == subject,
        )
    )
    if identity is not None:
        identity.raw_claims = json.dumps(claims, default=str)
        user = db.get(User, identity.user_id)
        if user is None or not user.is_active:
            return None
        return user

    email = claims.get("email")
    user: User | None = None
    if email:
        user = db.scalar(select(User).where(User.email == email))

    if user is None:
        if not settings.oidc_auto_create_users:
            return None
        is_admin = False
        if provider.admin_groups:
            groups = claims.get("groups") or []
            if isinstance(groups, list):
                is_admin = any(g in provider.admin_groups for g in groups)
        user = create_user(
            db,
            username=_make_username(claims, provider),
            password=None,
            email=email if isinstance(email, str) else None,
            display_name=claims.get("name") or claims.get("preferred_username"),
            is_admin=is_admin,
        )

    db.add(
        OIDCIdentity(
            user_id=user.id,
            provider=provider.name,
            subject=subject,
            raw_claims=json.dumps(claims, default=str),
        )
    )
    db.flush()
    return user

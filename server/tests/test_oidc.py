"""OIDC endpoint tests.

We don't talk to a real provider; we exercise the routing/config layer:
- /config/public lists configured providers when oidc_enabled
- /auth/oidc/<unknown>/login returns 404 when OIDC disabled
- /auth/oidc/<provider>/login returns 302 to issuer when enabled
- upsert_user_from_claims creates + relinks users
"""

from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from tangible.auth import oidc as oidc_service
from tangible.config import OIDCProvider, Settings, reset_settings_cache
from tangible.models import OIDCIdentity, User


def _enable_oidc(monkeypatch, settings: Settings) -> None:
    monkeypatch.setattr(settings, "oidc_enabled", True)
    monkeypatch.setattr(
        settings,
        "oidc_providers",
        [
            OIDCProvider(
                name="acme",
                display_name="Acme",
                issuer="https://issuer.example.com",
                client_id="cid",
                client_secret="csec",
            )
        ],
    )
    oidc_service.reset_registry()


def test_public_config_lists_providers_when_enabled(client, settings, monkeypatch) -> None:
    # Disabled by default
    body = client.get("/api/config/public").json()
    assert body["oidc_enabled"] is False
    assert body["oidc_providers"] == []

    _enable_oidc(monkeypatch, settings)
    body = client.get("/api/config/public").json()
    assert body["oidc_enabled"] is True
    assert body["oidc_providers"] == [
        {"name": "acme", "label": "Acme", "login_url": "/auth/oidc/acme/login"}
    ]


def test_oidc_login_404_when_disabled(client) -> None:
    r = client.get("/api/auth/oidc/acme/login", follow_redirects=False)
    assert r.status_code == 404


def test_oidc_login_404_for_unknown_provider(client, settings, monkeypatch) -> None:
    _enable_oidc(monkeypatch, settings)
    r = client.get("/api/auth/oidc/unknown/login", follow_redirects=False)
    assert r.status_code == 404


def test_upsert_creates_new_user(db: DBSession, settings, monkeypatch) -> None:
    _enable_oidc(monkeypatch, settings)
    provider = settings.oidc_providers[0]
    claims = {
        "sub": "user-42",
        "email": "alice@example.com",
        "name": "Alice",
        "preferred_username": "alice",
    }
    user = oidc_service.upsert_user_from_claims(
        db, settings=settings, provider=provider, claims=claims
    )
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.password_hash is None
    db.commit()

    identities = db.query(OIDCIdentity).all()
    assert len(identities) == 1
    assert identities[0].subject == "user-42"


def test_upsert_links_existing_email(db: DBSession, settings, monkeypatch) -> None:
    _enable_oidc(monkeypatch, settings)
    provider = settings.oidc_providers[0]
    db.add(
        User(
            username="bob",
            email="bob@example.com",
            password_hash=None,
        )
    )
    db.commit()

    user = oidc_service.upsert_user_from_claims(
        db,
        settings=settings,
        provider=provider,
        claims={"sub": "bob-sub", "email": "bob@example.com"},
    )
    assert user is not None
    assert user.username == "bob"
    db.commit()
    assert db.query(OIDCIdentity).count() == 1


def test_upsert_returns_none_without_subject(db: DBSession, settings, monkeypatch) -> None:
    _enable_oidc(monkeypatch, settings)
    provider = settings.oidc_providers[0]
    user = oidc_service.upsert_user_from_claims(
        db, settings=settings, provider=provider, claims={"email": "x@y.com"}
    )
    assert user is None


def test_upsert_respects_auto_create_off(db: DBSession, settings, monkeypatch) -> None:
    _enable_oidc(monkeypatch, settings)
    monkeypatch.setattr(settings, "oidc_auto_create_users", False)
    provider = settings.oidc_providers[0]
    user = oidc_service.upsert_user_from_claims(
        db,
        settings=settings,
        provider=provider,
        claims={"sub": "new", "email": "new@example.com"},
    )
    assert user is None


def test_upsert_admin_group_promotes(db: DBSession, settings, monkeypatch) -> None:
    _enable_oidc(monkeypatch, settings)
    provider = settings.oidc_providers[0]
    object.__setattr__(provider, "admin_groups", ["tangible-admins"])
    user = oidc_service.upsert_user_from_claims(
        db,
        settings=settings,
        provider=provider,
        claims={
            "sub": "admin-1",
            "email": "admin@example.com",
            "groups": ["tangible-admins", "other"],
        },
    )
    assert user is not None
    assert user.is_admin is True


def teardown_module() -> None:
    """Drop any registered authlib clients so the next test module is clean."""
    oidc_service.reset_registry()
    reset_settings_cache()

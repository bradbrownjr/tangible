"""End-to-end auth flow tests."""

from __future__ import annotations


def _register(client, username="alice", password="hunter22-secure"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@example.com"},
    )


def test_register_login_logout_me(client) -> None:
    r = _register(client)
    assert r.status_code == 201, r.text
    assert r.json()["username"] == "alice"

    r = client.post("/api/auth/login", json={"username": "alice", "password": "hunter22-secure"})
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "alice"

    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "alice"

    r = client.post("/api/auth/logout")
    assert r.status_code == 204

    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_register_disabled(client, monkeypatch) -> None:
    # First user is always allowed and becomes admin (first-run bootstrap).
    r = _register(client, username="alice")
    assert r.status_code == 201
    assert r.json()["is_admin"] is True

    # With users present, COVET_REGISTRATION_ENABLED gates additional signups.
    from covet.config import get_settings

    settings = get_settings()
    object.__setattr__(settings, "registration_enabled", False)

    r = _register(client, username="bob")
    assert r.status_code == 403


def test_first_user_is_admin(client) -> None:
    r = _register(client, username="root")
    assert r.status_code == 201
    assert r.json()["is_admin"] is True

    # Allow a second registration explicitly; that user must NOT be admin.
    from covet.config import get_settings

    settings = get_settings()
    object.__setattr__(settings, "registration_enabled", True)

    r = _register(client, username="second")
    assert r.status_code == 201
    assert r.json()["is_admin"] is False


def test_bad_login(client) -> None:
    _register(client)
    r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong-password"})
    assert r.status_code == 401


def test_api_token_auth(client) -> None:
    _register(client)
    client.post("/api/auth/login", json={"username": "alice", "password": "hunter22-secure"})
    r = client.post("/api/auth/tokens", params={"name": "test"})
    assert r.status_code == 201
    raw = r.json()["token"]
    assert raw

    # New client without cookies, using bearer token.
    from fastapi.testclient import TestClient

    bare = TestClient(client.app)
    r = bare.get("/api/auth/me", headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"

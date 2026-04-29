"""Health/version smoke tests."""

from __future__ import annotations


def test_healthz(client) -> None:
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz(client) -> None:
    r = client.get("/api/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_version(client) -> None:
    r = client.get("/api/version")
    assert r.status_code == 200
    assert "version" in r.json()


def test_public_config(client) -> None:
    r = client.get("/api/config/public")
    assert r.status_code == 200
    body = r.json()
    assert body["registration_enabled"] is True
    assert body["oidc_enabled"] is False

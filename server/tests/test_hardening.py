"""Tests for hardening middleware (security headers, CSRF, rate limit)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_security_headers_present(client: TestClient) -> None:
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in r.headers
    assert "Content-Security-Policy" in r.headers
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_security_headers_skip_csp_for_docs(client: TestClient) -> None:
    r = client.get("/api/docs")
    # Docs may or may not be enabled; what we care about is no CSP if it is.
    if r.status_code == 200:
        assert "Content-Security-Policy" not in r.headers


def test_csrf_blocks_cross_origin_cookie_post(client: TestClient) -> None:
    # Establish a session cookie via /auth/register + login.
    client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "correct horse battery staple",
            "email": "alice@example.com",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    # With cookie present + Origin from a foreign host → 403.
    r = client.post(
        "/api/collections",
        json={"name": "x"},
        headers={"Origin": "https://evil.example.com"},
    )
    assert r.status_code == 403
    assert "Cross-origin" in r.json()["detail"]


def test_csrf_allows_same_origin_cookie_post(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={
            "username": "bob",
            "password": "correct horse battery staple",
            "email": "bob@example.com",
        },
    )
    client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "correct horse battery staple"},
    )
    r = client.post(
        "/api/collections",
        json={"name": "books"},
        headers={"Origin": "http://testserver"},
    )
    assert r.status_code in (200, 201)


def test_csrf_exempts_bearer_auth(client: TestClient) -> None:
    # Register, mint a token, then call with bearer + cross-origin Origin.
    client.post(
        "/api/auth/register",
        json={
            "username": "carol",
            "password": "correct horse battery staple",
            "email": "carol@example.com",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "carol", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    tok = client.post("/api/auth/tokens", params={"name": "cli"}).json()
    raw = tok["token"]
    # Drop the session cookie so this request is bearer-only.
    client.cookies.clear()
    r = client.post(
        "/api/collections",
        json={"name": "movies"},
        headers={
            "Authorization": f"Bearer {raw}",
            "Origin": "https://anywhere.example.com",
        },
    )
    assert r.status_code in (200, 201)


def test_login_rate_limit_engages(client: TestClient) -> None:
    # Default login limit is 5/minute. The 6th attempt within the window
    # should be 429 regardless of credentials validity.
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "nope", "password": "nope"})
    r = client.post("/api/auth/login", json={"username": "nope", "password": "nope"})
    assert r.status_code == 429
    assert "Rate limit exceeded" in r.json()["detail"]

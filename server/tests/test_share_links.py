"""Share-link CRUD + public viewer tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _register(client, username, password="hunter22-secure"):
    r = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    assert r.status_code == 201, r.text


def _login(client, username, password="hunter22-secure"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _logout(client):
    client.post("/auth/logout")


def _setup_collection_with_item(client) -> tuple[str, str]:
    cid = client.post("/collections", json={"name": "Vinyl"}).json()["id"]
    iid = client.post(
        "/items",
        json={"collection_id": cid, "category": "music.vinyl", "title": "Kind of Blue"},
    ).json()["id"]
    return cid, iid


def test_create_and_use_share_link(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid, iid = _setup_collection_with_item(client)

    r = client.post(f"/collections/{cid}/share-links", json={"label": "Public"})
    assert r.status_code == 201, r.text
    body = r.json()
    slug = body["slug"]
    assert body["label"] == "Public"
    assert body["revoked"] is False

    # Anonymous can read collection + items via slug.
    _logout(client)
    r = client.get(f"/public/share/{slug}")
    assert r.status_code == 200
    assert r.json()["id"] == cid

    r = client.get(f"/public/share/{slug}/items")
    assert r.status_code == 200
    assert [it["id"] for it in r.json()] == [iid]


def test_unknown_slug_404(client) -> None:
    r = client.get("/public/share/does-not-exist")
    assert r.status_code == 404


def test_expired_share_returns_410(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid, _iid = _setup_collection_with_item(client)
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    r = client.post(
        f"/collections/{cid}/share-links",
        json={"expires_at": past},
    )
    assert r.status_code == 201
    slug = r.json()["slug"]
    _logout(client)
    r = client.get(f"/public/share/{slug}")
    assert r.status_code == 410


def test_revoked_share_404(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid, _iid = _setup_collection_with_item(client)
    r = client.post(f"/collections/{cid}/share-links", json={})
    link_id = r.json()["id"]
    slug = r.json()["slug"]

    assert client.delete(f"/collections/{cid}/share-links/{link_id}").status_code == 204
    _logout(client)
    assert client.get(f"/public/share/{slug}").status_code == 404


def test_non_owner_cannot_create_share_link(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid, _iid = _setup_collection_with_item(client)
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    _logout(client)
    _login(client, "bob")
    r = client.post(f"/collections/{cid}/share-links", json={})
    assert r.status_code == 403


def test_list_share_links(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid, _iid = _setup_collection_with_item(client)
    client.post(f"/collections/{cid}/share-links", json={"label": "A"})
    client.post(f"/collections/{cid}/share-links", json={"label": "B"})
    r = client.get(f"/collections/{cid}/share-links")
    assert r.status_code == 200
    assert len(r.json()) == 2

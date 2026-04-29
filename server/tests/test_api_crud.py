"""End-to-end CRUD tests for collections + items + tags + ACL."""

from __future__ import annotations


def _signup_and_login(client, username, password="hunter22-secure"):
    client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def test_collection_crud(client) -> None:
    _signup_and_login(client, "alice")

    r = client.post("/collections", json={"name": "Vinyl"})
    assert r.status_code == 201
    cid = r.json()["id"]

    r = client.get("/collections")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    r = client.patch(f"/collections/{cid}", json={"description": "My LPs"})
    assert r.status_code == 200
    assert r.json()["description"] == "My LPs"

    r = client.delete(f"/collections/{cid}")
    assert r.status_code == 204


def test_item_crud_and_acl(client) -> None:
    _signup_and_login(client, "alice")
    cid = client.post("/collections", json={"name": "Movies"}).json()["id"]

    r = client.post(
        "/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "The Matrix"},
    )
    assert r.status_code == 201
    iid = r.json()["id"]

    r = client.get("/items", params={"collection_id": cid})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/items/{iid}")
    assert r.status_code == 200

    r = client.patch(f"/items/{iid}", json={"condition": "VG+"})
    assert r.status_code == 200
    assert r.json()["condition"] == "VG+"

    # Second user has no access.
    client.post("/auth/logout")
    _signup_and_login(client, "bob")
    r = client.get(f"/items/{iid}")
    assert r.status_code == 403

    r = client.get("/items", params={"collection_id": cid})
    assert r.status_code == 403


def test_tag_crud(client) -> None:
    _signup_and_login(client, "alice")
    r = client.post("/tags", json={"name": "favorites", "color": "#ff0"})
    assert r.status_code == 201
    tid = r.json()["id"]

    r = client.get("/tags")
    assert any(t["id"] == tid for t in r.json())

    r = client.delete(f"/tags/{tid}")
    assert r.status_code == 204

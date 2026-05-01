"""Tests for hierarchical Location endpoints (Phase 11)."""

from __future__ import annotations


def _signup_and_login(client, username, password="hunter22-secure"):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text


def _make_collection(client, name="Loc test"):
    return client.post("/api/collections", json={"name": name}).json()["id"]


def test_location_crud_roundtrip(client) -> None:
    _signup_and_login(client, "loc-crud")
    cid = _make_collection(client)

    # Empty list to start
    r = client.get("/api/locations", params={"collection_id": cid})
    assert r.status_code == 200
    assert r.json() == []

    # Create root and child
    home = client.post(
        "/api/locations",
        json={"collection_id": cid, "name": "Home", "kind": "home"},
    )
    assert home.status_code == 201, home.text
    home_id = home.json()["id"]
    assert home.json()["item_count"] == 0

    garage = client.post(
        "/api/locations",
        json={
            "collection_id": cid,
            "name": "Garage",
            "kind": "room",
            "parent_id": home_id,
        },
    )
    assert garage.status_code == 201
    garage_id = garage.json()["id"]

    shelf = client.post(
        "/api/locations",
        json={
            "collection_id": cid,
            "name": "Shelf A",
            "kind": "container",
            "parent_id": garage_id,
        },
    )
    assert shelf.status_code == 201
    shelf_id = shelf.json()["id"]

    # Tree fetch returns nested children
    tree = client.get("/api/locations", params={"collection_id": cid}).json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Home"
    assert tree[0]["children"][0]["name"] == "Garage"
    assert tree[0]["children"][0]["children"][0]["name"] == "Shelf A"

    # Rename
    r = client.patch(
        f"/api/locations/{shelf_id}", json={"name": "Shelf 1"}
    )
    assert r.status_code == 200 and r.json()["name"] == "Shelf 1"

    # Cycle detection: cannot make Home a child of Shelf 1
    bad = client.patch(
        f"/api/locations/{home_id}", json={"parent_id": shelf_id}
    )
    assert bad.status_code == 422

    # Self-parent rejected
    self_bad = client.patch(
        f"/api/locations/{garage_id}", json={"parent_id": garage_id}
    )
    assert self_bad.status_code == 422

    # Cascade delete: remove garage removes shelf
    r = client.delete(f"/api/locations/{garage_id}")
    assert r.status_code == 204
    tree = client.get("/api/locations", params={"collection_id": cid}).json()
    assert tree[0]["children"] == []


def test_location_assignment_and_path(client) -> None:
    _signup_and_login(client, "loc-assign")
    cid = _make_collection(client)

    home = client.post(
        "/api/locations",
        json={"collection_id": cid, "name": "Home", "kind": "home"},
    ).json()
    kitchen = client.post(
        "/api/locations",
        json={
            "collection_id": cid,
            "name": "Kitchen",
            "kind": "room",
            "parent_id": home["id"],
        },
    ).json()
    pantry = client.post(
        "/api/locations",
        json={
            "collection_id": cid,
            "name": "Pantry",
            "kind": "zone",
            "parent_id": kitchen["id"],
        },
    ).json()

    item = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Box of stuff",
            "location_id": pantry["id"],
        },
    )
    assert item.status_code == 201, item.text
    body = item.json()
    assert body["location_id"] == pantry["id"]
    assert body["location_path"] == ["Home", "Kitchen", "Pantry"]

    # item_count rolls up (counts only direct assignments)
    tree = client.get("/api/locations", params={"collection_id": cid}).json()
    assert tree[0]["children"][0]["children"][0]["item_count"] == 1

    # Deleting the location nulls the item's reference
    r = client.delete(f"/api/locations/{pantry['id']}")
    assert r.status_code == 204
    fetched = client.get(f"/api/items/{body['id']}").json()
    assert fetched["location_id"] is None
    assert fetched["location_path"] is None


def test_location_cross_collection_rejected(client) -> None:
    _signup_and_login(client, "loc-cross")
    cid_a = _make_collection(client, name="A")
    cid_b = _make_collection(client, name="B")

    loc_a = client.post(
        "/api/locations",
        json={"collection_id": cid_a, "name": "A-room"},
    ).json()

    bad = client.post(
        "/api/items",
        json={
            "collection_id": cid_b,
            "category": "movies.dvd",
            "title": "Wrong scope",
            "location_id": loc_a["id"],
        },
    )
    assert bad.status_code == 422

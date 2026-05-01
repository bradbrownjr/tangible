"""Tests for manual / asset bundle endpoints (Phase 11)."""

from __future__ import annotations

import io


def _signup_and_login(client, username, password="hunter22-secure"):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text


def _make_collection(client, name="Bundle test"):
    return client.post("/api/collections", json={"name": name}).json()["id"]


def _make_item(client, cid, title="Drill"):
    return client.post(
        "/api/items", json={"collection_id": cid, "title": title, "category": "movies.dvd"}
    ).json()["id"]


def test_bundle_crud_and_asset_lifecycle(client) -> None:
    _signup_and_login(client, "bundle-crud")
    cid = _make_collection(client)

    # Empty list
    r = client.get(f"/api/collections/{cid}/bundles")
    assert r.status_code == 200 and r.json() == []

    # Create
    r = client.post(
        f"/api/collections/{cid}/bundles",
        json={"title": "DeWalt DCD777 Manual Bundle", "description": "20V drill"},
    )
    assert r.status_code == 201, r.text
    bundle = r.json()
    bid = bundle["id"]
    assert bundle["assets"] == []
    assert bundle["item_ids"] == []

    # Upload an asset (small text payload)
    payload = io.BytesIO(b"this is the manual")
    r = client.post(
        f"/api/bundles/{bid}/assets",
        files={"file": ("manual.txt", payload, "text/plain")},
        data={"label": "User manual", "kind": "manual", "sort_order": "0"},
    )
    assert r.status_code == 201, r.text
    asset = r.json()
    aid = asset["id"]
    assert asset["bundle_id"] == bid
    assert asset["kind"] == "manual"
    assert asset["byte_size"] == len(b"this is the manual")

    # Bundle now reports the asset
    r = client.get(f"/api/bundles/{bid}").json()
    assert len(r["assets"]) == 1
    assert r["assets"][0]["id"] == aid

    # Mark as primary
    r = client.patch(f"/api/bundles/{bid}", json={"primary_asset_id": aid})
    assert r.status_code == 200 and r.json()["primary_asset_id"] == aid

    # Update asset label/kind
    r = client.patch(
        f"/api/bundles/{bid}/assets/{aid}",
        json={"label": "Quickstart", "kind": "service"},
    )
    assert r.status_code == 200
    assert r.json()["label"] == "Quickstart"
    assert r.json()["kind"] == "service"

    # Download
    r = client.get(f"/api/bundles/{bid}/assets/{aid}/download")
    assert r.status_code == 200
    assert r.content == b"this is the manual"

    # Reject unknown kind (pydantic Literal rejection)
    r = client.patch(
        f"/api/bundles/{bid}/assets/{aid}", json={"kind": "bogus"}
    )
    assert r.status_code == 422

    # Delete asset → primary cleared
    r = client.delete(f"/api/bundles/{bid}/assets/{aid}")
    assert r.status_code == 204
    r = client.get(f"/api/bundles/{bid}").json()
    assert r["primary_asset_id"] is None
    assert r["assets"] == []


def test_bundle_item_linking(client) -> None:
    _signup_and_login(client, "bundle-link")
    cid = _make_collection(client)
    other_cid = _make_collection(client, name="Other")

    item_a = _make_item(client, cid, "Drill A")
    item_b = _make_item(client, cid, "Drill B")
    item_other = _make_item(client, other_cid, "Hose")

    bid = client.post(
        f"/api/collections/{cid}/bundles", json={"title": "Manual"}
    ).json()["id"]

    # Cross-collection item is rejected
    r = client.post(f"/api/bundles/{bid}/items/{item_other}")
    assert r.status_code == 400

    # Link two items
    assert client.post(f"/api/bundles/{bid}/items/{item_a}").status_code == 204
    assert client.post(f"/api/bundles/{bid}/items/{item_b}").status_code == 204

    # Idempotent re-link
    assert client.post(f"/api/bundles/{bid}/items/{item_a}").status_code == 204

    # Bundle reports both items
    r = client.get(f"/api/bundles/{bid}").json()
    assert sorted(r["item_ids"]) == sorted([item_a, item_b])

    # Item reports its bundle
    r = client.get(f"/api/items/{item_a}/bundles").json()
    assert len(r) == 1 and r[0]["id"] == bid

    # Unlink
    assert client.delete(f"/api/bundles/{bid}/items/{item_a}").status_code == 204
    r = client.get(f"/api/items/{item_a}/bundles").json()
    assert r == []

    # Deleting an item leaves the bundle (and the other link) intact
    assert client.delete(f"/api/items/{item_b}").status_code == 204
    r = client.get(f"/api/bundles/{bid}").json()
    assert r["item_ids"] == []


def test_bundle_permissions(client) -> None:
    _signup_and_login(client, "bundle-owner")
    cid = _make_collection(client)
    bid = client.post(
        f"/api/collections/{cid}/bundles", json={"title": "Owner bundle"}
    ).json()["id"]
    client.post("/api/auth/logout")

    _signup_and_login(client, "bundle-stranger")
    r = client.get(f"/api/collections/{cid}/bundles")
    assert r.status_code == 403
    r = client.get(f"/api/bundles/{bid}")
    assert r.status_code == 403
    r = client.post(
        f"/api/collections/{cid}/bundles", json={"title": "stranger"}
    )
    assert r.status_code == 403

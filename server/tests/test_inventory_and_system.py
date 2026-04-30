from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _signup_and_login(client, username: str, password: str = "hunter22-secure") -> None:
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _create_item(client) -> tuple[str, str]:
    cid = client.post("/api/collections", json={"name": "Pantry"}).json()["id"]
    r = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "other.generic", "title": "Milk"},
    )
    assert r.status_code == 201, r.text
    return cid, r.json()["id"]


def test_restock_creates_package_and_updates_item_state(client) -> None:
    _signup_and_login(client, "alice")
    _, item_id = _create_item(client)

    client.patch(f"/api/items/{item_id}", json={"depleted": True, "quantity": 0})

    purchased = datetime.now(UTC).isoformat()
    use_by = (datetime.now(UTC) + timedelta(days=7)).isoformat()

    r = client.post(
        f"/api/items/{item_id}/restock",
        json={"label": "Jug #2", "quantity": 2, "purchased_at": purchased, "use_by_date": use_by},
    )
    assert r.status_code == 201, r.text
    lot = r.json()
    assert lot["item_id"] == item_id
    assert lot["quantity"] == 2
    assert lot["is_active"] is True

    item = client.get(f"/api/items/{item_id}").json()
    assert item["depleted"] is False
    assert item["quantity"] == 2



def test_consuming_last_package_marks_item_depleted(client) -> None:
    _signup_and_login(client, "alice")
    cid, item_id = _create_item(client)

    r = client.post(
        f"/api/items/{item_id}/restock",
        json={"label": "Only jug", "quantity": 1},
    )
    assert r.status_code == 201, r.text
    lot_id = r.json()["id"]

    r = client.post(f"/api/lots/{lot_id}/consume")
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False

    item = client.get(f"/api/items/{item_id}").json()
    assert item["quantity"] == 0
    assert item["depleted"] is True

    grocery = client.get("/api/items/grocery-list").json()
    assert any(x["id"] == item_id for x in grocery)

    # Smoke check collection still accessible after lot mutations.
    r = client.get("/api/items", params={"collection_id": cid})
    assert r.status_code == 200



def test_alerts_include_item_lot_and_maintenance_due(client) -> None:
    _signup_and_login(client, "alice")
    _, item_id = _create_item(client)

    due_soon = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    client.patch(f"/api/items/{item_id}", json={"use_by_date": due_soon})
    client.post(
        f"/api/items/{item_id}/restock",
        json={"label": "Pack A", "quantity": 1, "use_by_date": due_soon},
    )
    client.post(
        f"/api/items/{item_id}/maintenance",
        json={"name": "Subscription renewal", "next_due_at": due_soon},
    )

    r = client.get("/api/alerts", params={"within_days": 7})
    assert r.status_code == 200, r.text
    kinds = {a["kind"] for a in r.json()}
    assert "item_use_by" in kinds
    assert "lot_use_by" in kinds
    assert "maintenance_due" in kinds



def test_admin_inventory_scrub_endpoint(client) -> None:
    _signup_and_login(client, "alice")
    _, _ = _create_item(client)

    # First user is admin and can scrub with confirmation phrase.
    bad = client.post("/api/admin/system/scrub-inventory", json={"confirmation": "nope"})
    assert bad.status_code == 422

    ok = client.post(
        "/api/admin/system/scrub-inventory",
        json={"confirmation": "SCRUB INVENTORY"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["scrubbed"] is True

    collections = client.get("/api/collections")
    assert collections.status_code == 200
    assert collections.json() == []

    # Non-admin user cannot scrub.
    client.post("/api/auth/logout")
    _signup_and_login(client, "bob")
    denied = client.post(
        "/api/admin/system/scrub-inventory",
        json={"confirmation": "SCRUB INVENTORY"},
    )
    assert denied.status_code == 403

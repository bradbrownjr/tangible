"""Maintenance + parent/child tests."""

from __future__ import annotations


def _register(client, username, password="hunter22-secure"):
    r = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    assert r.status_code == 201, r.text


def _login(client, username, password="hunter22-secure"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _setup(client, owner="alice"):
    _register(client, owner)
    _login(client, owner)
    cid = client.post("/collections", json={"name": "Garage"}).json()["id"]
    return cid


def test_maintenance_task_lifecycle(client) -> None:
    cid = _setup(client, "mech")
    iid = client.post(
        "/items", json={"collection_id": cid, "category": "tools.hand", "title": "Mower"}
    ).json()["id"]

    r = client.post(
        f"/items/{iid}/maintenance",
        json={"name": "Oil change", "interval_days": 30},
    )
    assert r.status_code == 201, r.text
    task = r.json()
    assert task["name"] == "Oil change"
    assert task["next_due_at"] is not None  # auto-computed

    r = client.post(f"/maintenance/{task['id']}/complete")
    assert r.status_code == 200
    assert r.json()["last_completed_at"] is not None

    r = client.get(f"/items/{iid}/maintenance")
    assert len(r.json()) == 1

    r = client.get("/maintenance?within_days=365")
    assert any(t["id"] == task["id"] for t in r.json())

    r = client.delete(f"/maintenance/{task['id']}")
    assert r.status_code == 204


def test_parent_child_items(client) -> None:
    cid = _setup(client, "kit")
    parent = client.post(
        "/items", json={"collection_id": cid, "category": "other.generic", "title": "Camera kit"}
    ).json()
    child = client.post(
        "/items",
        json={
            "collection_id": cid,
            "category": "other.generic",
            "title": "Lens",
            "parent_id": parent["id"],
        },
    ).json()
    assert child["parent_id"] == parent["id"]

    r = client.get(f"/items/{parent['id']}/children")
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == [child["id"]]


def test_parent_self_rejected(client) -> None:
    cid = _setup(client, "self")
    iid = client.post(
        "/items", json={"collection_id": cid, "category": "other.generic", "title": "X"}
    ).json()["id"]
    r = client.patch(f"/items/{iid}", json={"parent_id": iid})
    assert r.status_code == 422


def test_parent_cycle_rejected(client) -> None:
    cid = _setup(client, "cyc")
    a = client.post(
        "/items", json={"collection_id": cid, "category": "other.generic", "title": "A"}
    ).json()["id"]
    b = client.post(
        "/items",
        json={"collection_id": cid, "category": "other.generic", "title": "B", "parent_id": a},
    ).json()["id"]
    # Try to set A's parent to B -> would form A -> B -> A cycle.
    r = client.patch(f"/items/{a}", json={"parent_id": b})
    assert r.status_code == 422


def test_parent_must_be_same_collection(client) -> None:
    cid1 = _setup(client, "xcuser")
    cid2 = client.post("/collections", json={"name": "Other"}).json()["id"]
    a = client.post(
        "/items", json={"collection_id": cid1, "category": "other.generic", "title": "A"}
    ).json()["id"]
    b = client.post(
        "/items", json={"collection_id": cid2, "category": "other.generic", "title": "B"}
    ).json()["id"]
    r = client.patch(f"/items/{b}", json={"parent_id": a})
    assert r.status_code == 422

"""Phase 12 — completion history and chores tests."""

from __future__ import annotations


def _register(client, username, password="hunter22-secure"):
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    assert r.status_code == 201, r.text


def _login(client, username, password="hunter22-secure"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _setup(client, owner="alice"):
    _register(client, owner)
    _login(client, owner)
    cid = client.post("/api/collections", json={"name": "Home"}).json()["id"]
    return cid


def test_maintenance_completion_history(client) -> None:
    """complete_task records completion history with notes/cost and is paginated."""
    cid = _setup(client, "mechanic")
    iid = client.post(
        "/api/items", json={"collection_id": cid, "category": "movies.dvd", "title": "Generator"}
    ).json()["id"]
    tid = client.post(
        f"/api/items/{iid}/maintenance",
        json={"name": "Oil change", "interval_days": 90},
    ).json()["id"]

    # Complete twice with different metadata.
    r1 = client.post(
        f"/api/maintenance/{tid}/complete",
        json={"notes": "Used Mobil 1", "cost": "12.50", "currency": "USD", "technician": "self"},
    )
    assert r1.status_code == 200

    r2 = client.post(
        f"/api/maintenance/{tid}/complete",
        json={"notes": "Quick change", "odometer_reading": "1500.0", "hours_reading": "42.5"},
    )
    assert r2.status_code == 200

    # History should have 2 entries, newest first.
    h = client.get(f"/api/maintenance/{tid}/history").json()
    assert len(h) == 2
    assert h[0]["notes"] == "Quick change"
    assert h[0]["hours_reading"] == "42.50"
    assert h[1]["notes"] == "Used Mobil 1"
    assert h[1]["cost"] == "12.5000"

    # CSV export.
    r_csv = client.get(f"/api/maintenance/{tid}/history?format=csv")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert "Oil change" not in r_csv.text  # CSV has no task name
    assert "Quick change" in r_csv.text

    # Pagination.
    h_page = client.get(f"/api/maintenance/{tid}/history?limit=1&skip=1").json()
    assert len(h_page) == 1
    assert h_page[0]["notes"] == "Used Mobil 1"


def test_chore_lifecycle(client) -> None:
    """Full chore CRUD, complete with history, and appearance in alerts."""
    cid = _setup(client, "homeowner")

    # Create
    r = client.post(
        f"/api/collections/{cid}/chores",
        json={"name": "Clean gutters", "interval_days": 180, "notes": "Spring + fall"},
    )
    assert r.status_code == 201, r.text
    chore = r.json()
    assert chore["name"] == "Clean gutters"
    assert chore["next_due_at"] is not None  # auto-computed from now + 180d

    cid2 = chore["id"]

    # List
    chores = client.get(f"/api/collections/{cid}/chores").json()
    assert any(c["id"] == cid2 for c in chores)

    # Get
    assert client.get(f"/api/chores/{cid2}").json()["name"] == "Clean gutters"

    # Patch
    r = client.patch(f"/api/chores/{cid2}", json={"notes": "Use ladder"})
    assert r.status_code == 200
    assert r.json()["notes"] == "Use ladder"

    # Complete with metadata
    r = client.post(
        f"/api/chores/{cid2}/complete",
        json={"notes": "Done, replaced section A", "cost": "35.00", "currency": "USD"},
    )
    assert r.status_code == 200
    completed = r.json()
    assert completed["last_completed_at"] is not None
    assert completed["next_due_at"] is not None  # reset from now + 180d

    # History
    h = client.get(f"/api/chores/{cid2}/history").json()
    assert len(h) == 1
    assert h[0]["notes"] == "Done, replaced section A"
    assert h[0]["cost"] == "35.0000"

    # CSV history
    r_csv = client.get(f"/api/chores/{cid2}/history?format=csv")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]

    # Delete
    r = client.delete(f"/api/chores/{cid2}")
    assert r.status_code == 204
    assert client.get(f"/api/chores/{cid2}").status_code == 404


def test_chore_in_alerts(client) -> None:
    """Overdue chores appear in GET /alerts."""
    cid = _setup(client, "alertuser")

    from datetime import UTC, datetime, timedelta

    past = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    r = client.post(
        f"/api/collections/{cid}/chores",
        json={"name": "Test smoke detectors", "next_due_at": past},
    )
    assert r.status_code == 201
    chore_id = r.json()["id"]

    alerts = client.get("/api/alerts?within_days=30").json()
    chore_alerts = [a for a in alerts if a["kind"] == "chore_due"]
    assert any(a["id"] == f"chore-{chore_id}" for a in chore_alerts)
    matching = next(a for a in chore_alerts if a["id"] == f"chore-{chore_id}")
    assert matching["severity"] == "critical"  # past due


def test_chore_viewer_cannot_write(client) -> None:
    """Viewer can read chores but not create/complete/delete."""
    cid = _setup(client, "choreowner")
    _register(client, "choreview", "hunter22-secure")

    r = client.post(
        f"/api/collections/{cid}/chores",
        json={"name": "Mow lawn", "interval_days": 14},
    )
    assert r.status_code == 201
    chore_id = r.json()["id"]

    # Invite viewer.
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "choreview", "role": "viewer"},
    )
    assert r.status_code in (200, 201)

    _login(client, "choreview")

    assert client.get(f"/api/collections/{cid}/chores").status_code == 200
    assert client.get(f"/api/chores/{chore_id}").status_code == 200
    assert client.post(f"/api/chores/{chore_id}/complete").status_code == 403
    assert client.delete(f"/api/chores/{chore_id}").status_code == 403


def test_quick_chore(client) -> None:
    """POST /items/{id}/quick-chore finds-or-creates a chore and completes it."""
    cid = _setup(client, "quickuser")
    iid = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "home_equipment.generator", "title": "Honda Generator"},
    ).json()["id"]

    # First call creates the chore and completes it.
    r = client.post(
        f"/api/items/{iid}/quick-chore",
        json={"chore_name": "Honda Generator — run log", "interval_days": 30},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Honda Generator — run log"
    assert data["last_completed_at"] is not None
    assert data["next_due_at"] is not None
    chore_id = data["id"]

    # Second call reuses the same chore and adds another completion.
    r2 = client.post(
        f"/api/items/{iid}/quick-chore",
        json={"chore_name": "Honda Generator — run log", "interval_days": 30, "notes": "ran 20 min"},
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == chore_id  # same chore

    history = client.get(f"/api/chores/{chore_id}/history").json()
    assert len(history) == 2

    # Viewer cannot use quick-chore.
    _register(client, "quickview", "hunter22-secure")
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "quickview", "role": "viewer"},
    )
    _login(client, "quickview")
    assert client.post(
        f"/api/items/{iid}/quick-chore",
        json={"chore_name": "Honda Generator — run log"},
    ).status_code == 403

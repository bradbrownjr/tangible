"""Document attachment + expiry dashboard tests."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta


def _register(client, username, password="hunter22-secure"):
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    assert r.status_code == 201, r.text


def _login(client, username, password="hunter22-secure"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _setup_item(client, owner="alice"):
    _register(client, owner)
    _login(client, owner)
    cid = client.post("/api/collections", json={"name": "Stuff"}).json()["id"]
    iid = client.post(
        "/api/items", json={"collection_id": cid, "category": "tools.hand", "title": "Drill"}
    ).json()["id"]
    return cid, iid


def test_upload_and_download_pdf(client) -> None:
    _, iid = _setup_item(client)
    body = b"%PDF-1.4 fake\n"
    r = client.post(
        f"/api/items/{iid}/documents",
        files={"file": ("manual.pdf", io.BytesIO(body), "application/pdf")},
        data={"label": "User manual", "category": "manual"},
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["filename"] == "manual.pdf"
    assert doc["category"] == "manual"
    assert doc["byte_size"] == len(body)

    r = client.get(f"/api/items/{iid}/documents")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/api/documents/{doc['id']}/download")
    assert r.status_code == 200
    assert r.content == body


def test_upload_rejects_disallowed_mime(client) -> None:
    _, iid = _setup_item(client, owner="bob")
    r = client.post(
        f"/api/items/{iid}/documents",
        files={
            "file": ("evil.exe", io.BytesIO(b"MZ"), "application/x-msdownload"),
        },
    )
    assert r.status_code == 415


def test_delete_document(client) -> None:
    _, iid = _setup_item(client, owner="carol")
    r = client.post(
        f"/api/items/{iid}/documents",
        files={"file": ("t.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    did = r.json()["id"]
    r = client.delete(f"/api/documents/{did}")
    assert r.status_code == 204
    r = client.get(f"/api/documents/{did}/download")
    assert r.status_code == 404


def test_viewer_cannot_upload(client) -> None:
    _register(client, "owner1")
    _register(client, "viewer1")
    _login(client, "owner1")
    cid = client.post("/api/collections", json={"name": "Shared"}).json()["id"]
    iid = client.post(
        "/api/items", json={"collection_id": cid, "category": "other.generic", "title": "X"}
    ).json()["id"]
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "viewer1", "role": "viewer"},
    )
    client.post("/api/auth/logout")
    _login(client, "viewer1")
    r = client.post(
        f"/api/items/{iid}/documents",
        files={"file": ("t.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert r.status_code == 403


def test_expiring_dashboard(client) -> None:
    _, iid = _setup_item(client, owner="dave")
    soon = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    far = (datetime.now(UTC) + timedelta(days=400)).isoformat()

    # Item expiring soon
    client.patch(f"/api/items/{iid}", json={"expires_at": soon})
    # Doc expiring far in future
    client.post(
        f"/api/items/{iid}/documents",
        files={"file": ("w.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        data={"category": "warranty", "expires_at": far},
    )

    r = client.get("/api/expiring?within_days=30")
    assert r.status_code == 200
    rows = r.json()
    kinds = {r["kind"] for r in rows}
    assert "item" in kinds
    assert "document" not in kinds  # 400d > 30d

    r = client.get("/api/expiring?within_days=500")
    rows = r.json()
    assert {r["kind"] for r in rows} == {"item", "document"}

"""End-to-end tests for the import / backup / restore endpoints."""

from __future__ import annotations

import io
import json


def _signup_and_login(client, username: str, password: str = "hunter22-secure") -> None:
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _make_collection(client, name: str = "Imports") -> str:
    r = client.post("/api/collections", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def test_import_clz_movie(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client, "Movies")
    xml = (
        b"<movielist>"
        b"<movie><title>The Matrix</title><year>1999</year>"
        b"<barcode>012345678901</barcode></movie>"
        b"<movie><title>Blade Runner</title><year>1982</year></movie>"
        b"</movielist>"
    )
    r = client.post(
        "/api/imports/clz",
        data={"collection_id": cid, "flavor": "clz-movie"},
        files={"file": ("export.xml", io.BytesIO(xml), "application/xml")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2

    items = client.get("/api/items", params={"collection_id": cid}).json()
    titles = sorted(i["title"] for i in items)
    assert titles == ["Blade Runner", "The Matrix"]


def test_import_clz_unknown_flavor(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    r = client.post(
        "/api/imports/clz",
        data={"collection_id": cid, "flavor": "clz-bogus"},
        files={"file": ("x.xml", io.BytesIO(b"<x/>"), "application/xml")},
    )
    assert r.status_code == 400


def test_import_csv(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client, "Books")

    csv_text = b"Name,Year,ISBN\nDune,1965,9780441172719\nFoundation,1951,9780553293357\n"
    mapping = {
        "Name": "title",
        "Year": "attr:year",
        "ISBN": "id:isbn",
    }
    r = client.post(
        "/api/imports/csv",
        data={
            "collection_id": cid,
            "category": "books.print",
            "mapping": json.dumps(mapping),
        },
        files={"file": ("books.csv", io.BytesIO(csv_text), "text/csv")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == 2

    items = client.get("/api/items", params={"collection_id": cid}).json()
    assert {i["title"] for i in items} == {"Dune", "Foundation"}


def test_backup_and_restore_roundtrip(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client, "Originals")
    client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "The Matrix"},
    )
    client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Blade Runner"},
    )
    client.post("/api/tags", json={"name": "favorite", "color": "#ff0"})
    client.post("/api/contacts", json={"name": "Bob"})

    r = client.get("/api/imports/backup")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["version"] == 1
    assert len(payload["collections"]) == 1
    assert len(payload["items"]) == 2
    assert len(payload["tags"]) == 1

    # Restore into a fresh user.
    client.post("/api/auth/logout")
    _signup_and_login(client, "carol")
    r = client.post(
        "/api/imports/restore",
        files={
            "file": (
                "backup.json",
                io.BytesIO(json.dumps(payload).encode("utf-8")),
                "application/json",
            )
        },
    )
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["collections"] == 1
    assert stats["items"] == 2
    assert stats["tags"] == 1
    assert stats["contacts"] == 1

    # Carol now sees the imported data.
    cols = client.get("/api/collections").json()
    assert any(c["name"] == "Originals" for c in cols)


def test_restore_rejects_unknown_version(client) -> None:
    _signup_and_login(client, "alice")
    bad = json.dumps({"version": 99, "collections": []}).encode("utf-8")
    r = client.post(
        "/api/imports/restore",
        files={"file": ("b.json", io.BytesIO(bad), "application/json")},
    )
    assert r.status_code == 400

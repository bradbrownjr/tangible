"""End-to-end tests for the import / backup / restore endpoints."""

from __future__ import annotations

import csv
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


def test_csv_export_import_roundtrip_preserves_parent_child(client) -> None:
    _signup_and_login(client, "roundtrip")
    source_cid = _make_collection(client, "Hierarchy source")
    target_cid = _make_collection(client, "Hierarchy target")

    parent = client.post(
        "/api/items",
        json={"collection_id": source_cid, "category": "games.software", "title": "Console"},
    )
    assert parent.status_code == 201, parent.text
    parent_id = parent.json()["id"]

    child = client.post(
        "/api/items",
        json={
            "collection_id": source_cid,
            "category": "games.software",
            "title": "Controller",
            "parent_id": parent_id,
        },
    )
    assert child.status_code == 201, child.text

    exported = client.get("/api/imports/csv/export", params={"collection_id": source_cid})
    assert exported.status_code == 200, exported.text
    text = exported.text
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 2
    assert {r["Title"] for r in rows} == {"Console", "Controller"}
    assert any(r["Parent ref"] for r in rows)

    mapping = {
        "Item ref": "ref:item_ref",
        "Parent ref": "ref:parent_ref",
        "Category": "category_slug",
        "Title": "title",
        "Subtitle": "subtitle",
        "Notes": "notes",
        "Quantity": "quantity",
        "Condition": "condition",
        "Location": "location",
        "Currency": "currency",
        "Purchase price": "purchase_price",
        "Current value": "current_value",
    }
    imported = client.post(
        "/api/imports/csv",
        data={
            "collection_id": target_cid,
            "mapping": json.dumps(mapping),
        },
        files={"file": ("roundtrip.csv", io.BytesIO(text.encode("utf-8")), "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 2

    target_items = client.get("/api/items", params={"collection_id": target_cid}).json()
    by_title = {i["title"]: i for i in target_items}
    assert set(by_title) == {"Console", "Controller"}
    assert by_title["Controller"]["parent_id"] == by_title["Console"]["id"]

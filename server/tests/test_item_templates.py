"""Item template + per-type custom field validation tests."""

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


BOOK_FIELDS = [
    {"key": "isbn", "label": "ISBN", "type": "text", "required": True},
    {"key": "pages", "label": "Pages", "type": "number"},
    {"key": "signed", "label": "Signed", "type": "boolean", "default": False},
    {
        "key": "shelf",
        "label": "Shelf",
        "type": "select",
        "options": ["A", "B", "C"],
    },
]


def test_template_crud_and_attr_validation(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "Library"}).json()["id"]

    # Create template
    r = client.post(
        f"/collections/{cid}/templates",
        json={
            "name": "Hardcover Book",
            "item_type": "book",
            "description": "Bound books with ISBN",
            "fields": BOOK_FIELDS,
        },
    )
    assert r.status_code == 201, r.text
    tmpl_id = r.json()["id"]
    assert r.json()["fields"][0]["key"] == "isbn"

    # List shows it
    r = client.get(f"/collections/{cid}/templates")
    assert r.status_code == 200
    assert any(t["id"] == tmpl_id for t in r.json())

    # Item creation without required attr → 422
    r = client.post(
        "/items",
        json={
            "collection_id": cid,
            "type": "book",
            "title": "Dune",
            "template_id": tmpl_id,
            "attrs": {},
        },
    )
    assert r.status_code == 422, r.text

    # With required attr present → 201; default applied; coercion runs
    r = client.post(
        "/items",
        json={
            "collection_id": cid,
            "type": "book",
            "title": "Dune",
            "template_id": tmpl_id,
            "attrs": {"isbn": "978-0441172719", "pages": "658"},
        },
    )
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["template_id"] == tmpl_id
    assert item["attrs"]["pages"] == 658.0
    assert item["attrs"]["signed"] is False

    # Invalid select option rejected on update
    r = client.patch(
        f"/items/{item['id']}",
        json={"attrs": {"isbn": "978-0441172719", "shelf": "Z"}},
    )
    assert r.status_code == 422


def test_template_update_and_delete(client) -> None:
    _register(client, "carol")
    _login(client, "carol")
    cid = client.post("/collections", json={"name": "Tools"}).json()["id"]
    tmpl_id = client.post(
        f"/collections/{cid}/templates",
        json={"name": "Hand Tool", "item_type": "tool", "fields": []},
    ).json()["id"]

    r = client.patch(
        f"/templates/{tmpl_id}",
        json={
            "name": "Hand Tool v2",
            "fields": [
                {"key": "brand", "label": "Brand", "type": "text", "required": True}
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Hand Tool v2"

    # Now items missing 'brand' should fail
    r = client.post(
        "/items",
        json={
            "collection_id": cid,
            "type": "tool",
            "title": "Hammer",
            "template_id": tmpl_id,
        },
    )
    assert r.status_code == 422

    r = client.delete(f"/templates/{tmpl_id}")
    assert r.status_code == 204
    r = client.get(f"/templates/{tmpl_id}")
    assert r.status_code == 404


def test_template_unknown_id_rejected(client) -> None:
    _register(client, "dave")
    _login(client, "dave")
    cid = client.post("/collections", json={"name": "Misc"}).json()["id"]

    r = client.post(
        "/items",
        json={
            "collection_id": cid,
            "type": "generic",
            "title": "X",
            "template_id": "01ZZZZZZZZZZZZZZZZZZZZZZZZ",
        },
    )
    assert r.status_code == 422


def test_template_other_collection_rejected(client) -> None:
    _register(client, "eve")
    _login(client, "eve")
    cid_a = client.post("/collections", json={"name": "A"}).json()["id"]
    cid_b = client.post("/collections", json={"name": "B"}).json()["id"]

    tmpl_b = client.post(
        f"/collections/{cid_b}/templates",
        json={"name": "T", "item_type": "generic", "fields": []},
    ).json()["id"]

    r = client.post(
        "/items",
        json={
            "collection_id": cid_a,
            "type": "generic",
            "title": "X",
            "template_id": tmpl_b,
        },
    )
    assert r.status_code == 422


def test_viewer_cannot_create_template(client) -> None:
    _register(client, "owner1")
    _register(client, "viewer1")
    _login(client, "owner1")
    cid = client.post("/collections", json={"name": "Shared"}).json()["id"]
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "viewer1", "role": "viewer"},
    )
    client.post("/auth/logout")

    _login(client, "viewer1")
    r = client.post(
        f"/collections/{cid}/templates",
        json={"name": "T", "item_type": "generic", "fields": []},
    )
    assert r.status_code == 403

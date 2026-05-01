"""End-to-end CRUD tests for collections + items + tags + ACL."""

from __future__ import annotations


def _signup_and_login(client, username, password="hunter22-secure"):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def test_collection_crud(client) -> None:
    _signup_and_login(client, "alice")

    r = client.post("/api/collections", json={"name": "Vinyl"})
    assert r.status_code == 201
    cid = r.json()["id"]

    r = client.get("/api/collections")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    r = client.patch(f"/api/collections/{cid}", json={"description": "My LPs"})
    assert r.status_code == 200
    assert r.json()["description"] == "My LPs"

    r = client.delete(f"/api/collections/{cid}")
    assert r.status_code == 204


def test_item_crud_and_acl(client) -> None:
    _signup_and_login(client, "alice")
    cid = client.post("/api/collections", json={"name": "Movies"}).json()["id"]

    r = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "The Matrix"},
    )
    assert r.status_code == 201
    iid = r.json()["id"]

    r = client.get("/api/items", params={"collection_id": cid})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"/api/items/{iid}")
    assert r.status_code == 200

    r = client.patch(f"/api/items/{iid}", json={"condition": "VG+"})
    assert r.status_code == 200
    assert r.json()["condition"] == "VG+"

    # Second user has no access.
    client.post("/api/auth/logout")
    _signup_and_login(client, "bob")
    r = client.get(f"/api/items/{iid}")
    assert r.status_code == 403

    r = client.get("/api/items", params={"collection_id": cid})
    assert r.status_code == 403


def test_tag_crud(client) -> None:
    _signup_and_login(client, "alice")
    r = client.post("/api/tags", json={"name": "favorites", "color": "#ff0"})
    assert r.status_code == 201
    tid = r.json()["id"]

    r = client.get("/api/tags")
    assert any(t["id"] == tid for t in r.json())

    r = client.delete(f"/api/tags/{tid}")
    assert r.status_code == 204


def test_item_list_sort_options(client) -> None:
    _signup_and_login(client, "sorter")
    cid = client.post("/api/collections", json={"name": "Sort test"}).json()["id"]

    payloads = [
        {
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Bravo",
            "current_value": "25.00",
            "acquired_at": "2024-05-01T00:00:00Z",
            "attrs": {"creator": "Nolan"},
        },
        {
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Alpha",
            "current_value": "10.00",
            "acquired_at": "2024-01-01T00:00:00Z",
            "attrs": {"creator": "Kubrick"},
        },
        {
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Charlie",
            "current_value": "5.00",
            "acquired_at": "2023-12-01T00:00:00Z",
            "attrs": {"creator": "Anderson"},
        },
    ]
    for payload in payloads:
        r = client.post("/api/items", json=payload)
        assert r.status_code == 201, r.text

    r = client.get(
        "/api/items",
        params={"collection_id": cid, "sort_by": "value", "sort_dir": "desc"},
    )
    assert r.status_code == 200
    assert [x["title"] for x in r.json()] == ["Bravo", "Alpha", "Charlie"]

    r = client.get(
        "/api/items",
        params={"collection_id": cid, "sort_by": "acquired_at", "sort_dir": "asc"},
    )
    assert r.status_code == 200
    assert [x["title"] for x in r.json()] == ["Charlie", "Alpha", "Bravo"]

    r = client.get(
        "/api/items",
        params={
            "collection_id": cid,
            "sort_by": "attr",
            "sort_attr": "creator",
            "sort_dir": "asc",
        },
    )
    assert r.status_code == 200
    assert [x["title"] for x in r.json()] == ["Charlie", "Alpha", "Bravo"]

    r = client.get(
        "/api/items",
        params={"collection_id": cid, "sort_by": "attr", "sort_dir": "asc"},
    )
    assert r.status_code == 422


def test_parent_item_value_rollup(client) -> None:
    _signup_and_login(client, "rollup")
    cid = client.post("/api/collections", json={"name": "Kits"}).json()["id"]

    parent = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "tabletop.board_game", "title": "Starter Kit"},
    )
    assert parent.status_code == 201, parent.text
    parent_id = parent.json()["id"]

    child = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "tabletop.board_game",
            "title": "Core Box",
            "parent_id": parent_id,
            "current_value": "30.00",
        },
    )
    assert child.status_code == 201, child.text
    child_id = child.json()["id"]

    grandchild = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "tabletop.board_game",
            "title": "Sleeves",
            "parent_id": child_id,
            "current_value": "12.50",
        },
    )
    assert grandchild.status_code == 201, grandchild.text

    r = client.get("/api/items", params={"collection_id": cid})
    assert r.status_code == 200
    by_title = {x["title"]: x for x in r.json()}
    assert by_title["Starter Kit"]["rollup_current_value"] == "12.50"
    assert by_title["Core Box"]["rollup_current_value"] == "12.50"
    assert by_title["Sleeves"]["rollup_current_value"] is None

    r = client.get(f"/api/items/{parent_id}")
    assert r.status_code == 200
    assert r.json()["rollup_current_value"] == "12.50"


def test_item_flagging_and_auto_clear_on_edit(client) -> None:
    _signup_and_login(client, "flags")
    cid = client.post("/api/collections", json={"name": "Review queue"}).json()["id"]

    created = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Blade Runner"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    flagged = client.post(f"/api/items/{item_id}/flag", json={"note": "verify location"})
    assert flagged.status_code == 200, flagged.text
    assert flagged.json()["flagged_note"] == "verify location"
    assert flagged.json()["flagged_at"] is not None

    listed = client.get("/api/items", params={"collection_id": cid, "flagged": "true"})
    assert listed.status_code == 200
    assert [x["id"] for x in listed.json()] == [item_id]

    unflagged = client.delete(f"/api/items/{item_id}/flag")
    assert unflagged.status_code == 200, unflagged.text
    assert unflagged.json()["flagged_note"] is None
    assert unflagged.json()["flagged_at"] is None

    client.post(f"/api/items/{item_id}/flag", json={"note": "needs photo"})
    edited = client.patch(f"/api/items/{item_id}", json={"condition": "NM"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["condition"] == "NM"
    assert edited.json()["flagged_note"] is None
    assert edited.json()["flagged_at"] is None


def test_item_flagging_requires_editor_role(client) -> None:
    _signup_and_login(client, "owner")
    cid = client.post("/api/collections", json={"name": "Shared"}).json()["id"]
    item_id = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Alien"},
    ).json()["id"]
    client.post(
        "/api/auth/register",
        json={"username": "viewer", "password": "hunter22-secure", "email": "viewer@x.io"},
    )
    add_viewer = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "viewer", "role": "viewer"},
    )
    assert add_viewer.status_code == 201, add_viewer.text

    client.post("/api/auth/logout")
    login = client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": "hunter22-secure"},
    )
    assert login.status_code == 200, login.text

    denied_flag = client.post(f"/api/items/{item_id}/flag", json={"note": "check"})
    assert denied_flag.status_code == 403

    denied_unflag = client.delete(f"/api/items/{item_id}/flag")
    assert denied_unflag.status_code == 403


def test_item_wanted_flag_and_filter(client) -> None:
    _signup_and_login(client, "wanted")
    cid = client.post("/api/collections", json={"name": "Wishlist"}).json()["id"]

    owned = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Owned Game"},
    )
    assert owned.status_code == 201, owned.text

    wanted = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Wanted Game",
            "wanted": True,
        },
    )
    assert wanted.status_code == 201, wanted.text
    wanted_id = wanted.json()["id"]
    assert wanted.json()["wanted"] is True

    listed_wanted = client.get("/api/items", params={"collection_id": cid, "wanted": "true"})
    assert listed_wanted.status_code == 200, listed_wanted.text
    assert [x["title"] for x in listed_wanted.json()] == ["Wanted Game"]

    listed_owned = client.get("/api/items", params={"collection_id": cid, "wanted": "false"})
    assert listed_owned.status_code == 200, listed_owned.text
    assert [x["title"] for x in listed_owned.json()] == ["Owned Game"]

    patched = client.patch(f"/api/items/{wanted_id}", json={"wanted": False})
    assert patched.status_code == 200, patched.text
    assert patched.json()["wanted"] is False

    listed_after = client.get("/api/items", params={"collection_id": cid, "wanted": "true"})
    assert listed_after.status_code == 200, listed_after.text
    assert listed_after.json() == []

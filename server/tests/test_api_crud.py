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


def test_item_search_matches_notes_and_attrs(client) -> None:
    _signup_and_login(client, "searcher")
    cid = client.post("/api/collections", json={"name": "Search"}).json()["id"]

    alpha = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Generic title",
            "notes": "stored on top shelf",
            "attrs": {"creator": "Ridley Scott"},
        },
    )
    assert alpha.status_code == 201, alpha.text

    beta = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Other"},
    )
    assert beta.status_code == 201, beta.text

    by_note = client.get("/api/items", params={"collection_id": cid, "search": "top shelf"})
    assert by_note.status_code == 200, by_note.text
    assert [x["title"] for x in by_note.json()] == ["Generic title"]

    by_attr = client.get("/api/items", params={"collection_id": cid, "search": "ridley"})
    assert by_attr.status_code == 200, by_attr.text
    assert [x["title"] for x in by_attr.json()] == ["Generic title"]


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

    patched = client.patch(
        f"/api/items/{wanted_id}",
        json={
            "wanted": False,
            "acquired_at": "2026-05-01T12:00:00Z",
            "purchase_price": "24.99",
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["wanted"] is False
    assert str(patched.json()["acquired_at"]).startswith("2026-05-01T12:00:00")
    assert patched.json()["purchase_price"] == "24.99"

    listed_after = client.get("/api/items", params={"collection_id": cid, "wanted": "true"})
    assert listed_after.status_code == 200, listed_after.text
    assert listed_after.json() == []


def test_item_bulk_patch_and_delete(client) -> None:
    _signup_and_login(client, "bulkowner")
    cid = client.post("/api/collections", json={"name": "Bulk ops"}).json()["id"]
    other_cid = client.post("/api/collections", json={"name": "Elsewhere"}).json()["id"]

    first = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Bulk A"},
    )
    second = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Bulk B"},
    )
    outside = client.post(
        "/api/items",
        json={"collection_id": other_cid, "category": "movies.dvd", "title": "Outside"},
    )
    assert first.status_code == 201 and second.status_code == 201 and outside.status_code == 201
    id_a = first.json()["id"]
    id_b = second.json()["id"]
    outside_id = outside.json()["id"]

    patched = client.post(
        "/api/items/bulk-patch",
        json={"collection_id": cid, "item_ids": [id_a, id_b], "depleted": True, "wanted": True},
    )
    assert patched.status_code == 200, patched.text
    assert [x["id"] for x in patched.json()] == [id_a, id_b]
    assert all(x["depleted"] is True for x in patched.json())
    assert all(x["wanted"] is True for x in patched.json())

    wanted = client.get("/api/items", params={"collection_id": cid, "wanted": "true"})
    assert wanted.status_code == 200, wanted.text
    assert sorted(x["id"] for x in wanted.json()) == sorted([id_a, id_b])

    denied = client.post(
        "/api/items/bulk-patch",
        json={"collection_id": cid, "item_ids": [id_a, outside_id], "wanted": False},
    )
    assert denied.status_code == 404

    deleted = client.post(
        "/api/items/bulk-delete",
        json={"collection_id": cid, "item_ids": [id_a]},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] == 1

    remaining = client.get("/api/items", params={"collection_id": cid})
    assert remaining.status_code == 200
    assert [x["id"] for x in remaining.json()] == [id_b]


def test_item_bulk_tag_add_and_remove(client) -> None:
    _signup_and_login(client, "bulktag")
    cid = client.post("/api/collections", json={"name": "Bulk tags"}).json()["id"]

    first = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Tagged A"},
    )
    second = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Tagged B"},
    )
    assert first.status_code == 201 and second.status_code == 201
    id_a = first.json()["id"]
    id_b = second.json()["id"]

    tag = client.post("/api/tags", json={"name": "roadmap", "color": "#0af"})
    assert tag.status_code == 201, tag.text
    tag_id = tag.json()["id"]

    added = client.post(
        "/api/items/bulk-tags",
        json={
            "collection_id": cid,
            "item_ids": [id_a, id_b],
            "tag_ids": [tag_id],
            "mode": "add",
        },
    )
    assert added.status_code == 200, added.text
    assert [x["id"] for x in added.json()] == [id_a, id_b]

    tags_a = client.get(f"/api/items/{id_a}/tags")
    tags_b = client.get(f"/api/items/{id_b}/tags")
    assert tags_a.status_code == 200 and tags_b.status_code == 200
    assert [t["id"] for t in tags_a.json()] == [tag_id]
    assert [t["id"] for t in tags_b.json()] == [tag_id]

    removed = client.post(
        "/api/items/bulk-tags",
        json={
            "collection_id": cid,
            "item_ids": [id_b],
            "tag_ids": [tag_id],
            "mode": "remove",
        },
    )
    assert removed.status_code == 200, removed.text

    tags_a_after = client.get(f"/api/items/{id_a}/tags")
    tags_b_after = client.get(f"/api/items/{id_b}/tags")
    assert [t["id"] for t in tags_a_after.json()] == [tag_id]
    assert tags_b_after.json() == []


def test_item_bulk_tag_requires_editor_role(client) -> None:
    _signup_and_login(client, "bulktagowner")
    cid = client.post("/api/collections", json={"name": "Bulk tag ACL"}).json()["id"]
    created = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "ACL item"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    tag = client.post("/api/tags", json={"name": "private", "color": "#f0a"})
    assert tag.status_code == 201, tag.text
    tag_id = tag.json()["id"]

    client.post(
        "/api/auth/register",
        json={"username": "bulktagviewer", "password": "hunter22-secure", "email": "btv@x.io"},
    )
    add_viewer = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bulktagviewer", "role": "viewer"},
    )
    assert add_viewer.status_code == 201, add_viewer.text

    client.post("/api/auth/logout")
    login = client.post(
        "/api/auth/login",
        json={"username": "bulktagviewer", "password": "hunter22-secure"},
    )
    assert login.status_code == 200, login.text

    denied = client.post(
        "/api/items/bulk-tags",
        json={"collection_id": cid, "item_ids": [item_id], "tag_ids": [tag_id], "mode": "add"},
    )
    assert denied.status_code == 403


def test_item_bulk_move_location_and_category(client) -> None:
    _signup_and_login(client, "bulkmove")
    cid = client.post("/api/collections", json={"name": "Bulk move"}).json()["id"]

    first = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Move A"},
    )
    second = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Move B"},
    )
    assert first.status_code == 201 and second.status_code == 201
    id_a = first.json()["id"]
    id_b = second.json()["id"]

    moved = client.post(
        "/api/items/bulk-patch",
        json={
            "collection_id": cid,
            "item_ids": [id_a, id_b],
            "location": "Garage shelf A",
            "category": "tools.power",
        },
    )
    assert moved.status_code == 200, moved.text
    assert [x["id"] for x in moved.json()] == [id_a, id_b]
    assert all(x["location"] == "Garage shelf A" for x in moved.json())
    assert all(x["category_slug"] == "tools.power" for x in moved.json())

    cleared = client.post(
        "/api/items/bulk-patch",
        json={"collection_id": cid, "item_ids": [id_b], "location": ""},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()[0]["location"] is None


def test_item_bulk_lend_creates_loans(client) -> None:
    _signup_and_login(client, "bulklend")
    cid = client.post("/api/collections", json={"name": "Bulk lend"}).json()["id"]

    first = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Lend A"},
    )
    second = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Lend B"},
    )
    assert first.status_code == 201 and second.status_code == 201
    id_a = first.json()["id"]
    id_b = second.json()["id"]

    contact = client.post(
        "/api/contacts",
        json={"name": "Sam Borrower", "email": "sam@example.com"},
    )
    assert contact.status_code == 201, contact.text
    contact_id = contact.json()["id"]

    lent = client.post(
        "/api/items/bulk-lend",
        json={
            "collection_id": cid,
            "item_ids": [id_a, id_b],
            "contact_id": contact_id,
            "due_at": "2026-06-15T10:30:00Z",
            "notes": "Family loan",
        },
    )
    assert lent.status_code == 200, lent.text
    assert [x["item_id"] for x in lent.json()] == [id_a, id_b]
    assert all(x["contact_id"] == contact_id for x in lent.json())
    assert all(str(x["due_at"]).startswith("2026-06-15T10:30:00") for x in lent.json())

    listed_a = client.get("/api/loans", params={"item_id": id_a})
    assert listed_a.status_code == 200, listed_a.text
    assert len(listed_a.json()) == 1
    assert listed_a.json()[0]["contact_id"] == contact_id

    duplicate = client.post(
        "/api/items/bulk-lend",
        json={"collection_id": cid, "item_ids": [id_a], "contact_id": contact_id},
    )
    assert duplicate.status_code == 422


def test_item_bulk_actions_require_editor_role(client) -> None:
    _signup_and_login(client, "bulkowner2")
    cid = client.post("/api/collections", json={"name": "Shared bulk"}).json()["id"]
    created = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Shared item"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    client.post(
        "/api/auth/register",
        json={"username": "bulkviewer", "password": "hunter22-secure", "email": "bulkviewer@x.io"},
    )
    add_viewer = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bulkviewer", "role": "viewer"},
    )
    assert add_viewer.status_code == 201, add_viewer.text

    client.post("/api/auth/logout")
    login = client.post(
        "/api/auth/login",
        json={"username": "bulkviewer", "password": "hunter22-secure"},
    )
    assert login.status_code == 200, login.text

    denied_patch = client.post(
        "/api/items/bulk-patch",
        json={"collection_id": cid, "item_ids": [item_id], "depleted": True},
    )
    assert denied_patch.status_code == 403

    denied_delete = client.post(
        "/api/items/bulk-delete",
        json={"collection_id": cid, "item_ids": [item_id]},
    )
    assert denied_delete.status_code == 403

    denied_archive = client.post(
        "/api/items/bulk-archive",
        json={"collection_id": cid, "item_ids": [item_id], "disposition_type": "archived"},
    )
    assert denied_archive.status_code == 403

    denied_restore = client.post(
        "/api/items/bulk-restore",
        json={"collection_id": cid, "item_ids": [item_id]},
    )
    assert denied_restore.status_code == 403

    denied_lend = client.post(
        "/api/items/bulk-lend",
        json={"collection_id": cid, "item_ids": [item_id], "contact_id": "01HNOTREALCONTACTID000000000"},
    )
    assert denied_lend.status_code == 403


def test_item_bulk_archive_and_restore(client) -> None:
    _signup_and_login(client, "bulkarchive")
    cid = client.post("/api/collections", json={"name": "Bulk archive"}).json()["id"]

    first = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Archived A",
            "wanted": True,
            "depleted": True,
        },
    )
    second = client.post(
        "/api/items",
        json={
            "collection_id": cid,
            "category": "movies.dvd",
            "title": "Archived B",
            "wanted": True,
            "depleted": True,
        },
    )
    assert first.status_code == 201 and second.status_code == 201
    id_a = first.json()["id"]
    id_b = second.json()["id"]

    archived = client.post(
        "/api/items/bulk-archive",
        json={
            "collection_id": cid,
            "item_ids": [id_a, id_b],
            "disposition_type": "sold",
            "disposition_amount": "9.99",
            "disposition_buyer": "Bulk buyer",
        },
    )
    assert archived.status_code == 200, archived.text
    assert [x["id"] for x in archived.json()] == [id_a, id_b]
    assert all(x["archived_at"] is not None for x in archived.json())
    assert all(x["disposition_type"] == "sold" for x in archived.json())
    assert all(x["wanted"] is False for x in archived.json())
    assert all(x["depleted"] is False for x in archived.json())

    active = client.get("/api/items", params={"collection_id": cid})
    assert active.status_code == 200
    assert active.json() == []

    archived_only = client.get(
        "/api/items",
        params={"collection_id": cid, "include_archived": "true", "archived": "true"},
    )
    assert archived_only.status_code == 200, archived_only.text
    assert sorted(x["id"] for x in archived_only.json()) == sorted([id_a, id_b])

    restored = client.post(
        "/api/items/bulk-restore",
        json={"collection_id": cid, "item_ids": [id_a, id_b]},
    )
    assert restored.status_code == 200, restored.text
    assert all(x["archived_at"] is None for x in restored.json())
    assert all(x["disposition_type"] is None for x in restored.json())

    active_again = client.get("/api/items", params={"collection_id": cid})
    assert active_again.status_code == 200
    assert sorted(x["id"] for x in active_again.json()) == sorted([id_a, id_b])


def test_item_archive_restore_workflow(client) -> None:
    _signup_and_login(client, "archive")
    cid = client.post("/api/collections", json={"name": "Archive flow"}).json()["id"]
    created = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "Old DVD"},
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    archived = client.post(
        f"/api/items/{item_id}/archive",
        json={
            "disposition_type": "sold",
            "disposition_amount": "12.50",
            "disposition_buyer": "Local buyer",
            "disposition_note": "Garage sale",
            "disposition_at": "2026-05-01T10:00:00Z",
        },
    )
    assert archived.status_code == 200, archived.text
    body = archived.json()
    assert body["archived_at"] is not None
    assert body["disposition_type"] == "sold"
    assert body["disposition_amount"] == "12.50"
    assert body["disposition_buyer"] == "Local buyer"

    active = client.get("/api/items", params={"collection_id": cid})
    assert active.status_code == 200
    assert active.json() == []

    archived_only = client.get(
        "/api/items",
        params={"collection_id": cid, "include_archived": "true", "archived": "true"},
    )
    assert archived_only.status_code == 200
    assert [x["id"] for x in archived_only.json()] == [item_id]

    restored = client.post(f"/api/items/{item_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived_at"] is None
    assert restored.json()["disposition_type"] is None

    active_again = client.get("/api/items", params={"collection_id": cid})
    assert active_again.status_code == 200
    assert [x["id"] for x in active_again.json()] == [item_id]


def test_item_archive_restore_requires_editor_role(client) -> None:
    _signup_and_login(client, "archive_owner")
    cid = client.post("/api/collections", json={"name": "Archive ACL"}).json()["id"]
    item_id = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "movies.dvd", "title": "ACL item"},
    ).json()["id"]
    client.post(
        "/api/auth/register",
        json={"username": "archive_viewer", "password": "hunter22-secure", "email": "av@x.io"},
    )
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "archive_viewer", "role": "viewer"},
    )

    client.post("/api/auth/logout")
    client.post(
        "/api/auth/login",
        json={"username": "archive_viewer", "password": "hunter22-secure"},
    )

    denied_archive = client.post(f"/api/items/{item_id}/archive", json={"disposition_type": "disposed"})
    assert denied_archive.status_code == 403

    denied_restore = client.post(f"/api/items/{item_id}/restore")
    assert denied_restore.status_code == 403

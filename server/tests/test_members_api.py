"""Membership endpoint tests."""

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


def _logout(client):
    client.post("/api/auth/logout")


def test_owner_in_member_list(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "Vinyl"}).json()["id"]

    r = client.get(f"/api/collections/{cid}/members")
    assert r.status_code == 200
    members = r.json()
    assert len(members) == 1
    assert members[0]["role"] == "owner"
    assert members[0]["username"] == "alice"


def test_add_remove_member_flow(client) -> None:
    _register(client, "alice")
    _register(client, "bob")

    # As alice: create collection, add bob, then demote+remove him afterward.
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "Movies"}).json()["id"]
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    assert r.status_code == 201, r.text
    member_id = r.json()["id"]
    assert r.json()["role"] == "editor"
    assert r.json()["username"] == "bob"
    _logout(client)

    # As bob: can list members; cannot change roles.
    _login(client, "bob")
    r = client.get(f"/api/collections/{cid}/members")
    assert r.status_code == 200
    assert {m["username"] for m in r.json()} == {"alice", "bob"}
    r = client.patch(
        f"/api/collections/{cid}/members/{member_id}",
        json={"role": "viewer"},
    )
    assert r.status_code == 403
    _logout(client)

    # As alice: demote then remove bob.
    _login(client, "alice")
    r = client.patch(
        f"/api/collections/{cid}/members/{member_id}",
        json={"role": "viewer"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"
    assert client.delete(f"/api/collections/{cid}/members/{member_id}").status_code == 204
    _logout(client)

    # Bob has lost access.
    _login(client, "bob")
    assert client.get(f"/api/collections/{cid}/members").status_code == 403


def test_add_member_by_email(client) -> None:
    _register(client, "alice")
    _register(client, "carol")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "Tools"}).json()["id"]
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "carol@x.io", "role": "viewer"},
    )
    assert r.status_code == 201
    assert r.json()["username"] == "carol"


def test_cannot_add_unknown_user(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "X"}).json()["id"]
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "ghost", "role": "viewer"},
    )
    assert r.status_code == 404


def test_cannot_add_owner_as_member(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "X"}).json()["id"]
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "alice", "role": "viewer"},
    )
    assert r.status_code == 409


def test_cannot_double_add(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "X"}).json()["id"]
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    assert r.status_code == 201
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "viewer"},
    )
    assert r.status_code == 409


def test_non_owner_cannot_add_members(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "X"}).json()["id"]
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    _logout(client)
    _login(client, "bob")
    r = client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "alice", "role": "viewer"},
    )
    assert r.status_code == 403


def test_editor_can_modify_items_viewer_cannot(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _register(client, "carol")
    _login(client, "alice")
    cid = client.post("/api/collections", json={"name": "X"}).json()["id"]
    iid = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "other.generic", "title": "thing"},
    ).json()["id"]
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "carol", "role": "viewer"},
    )
    _logout(client)

    _login(client, "bob")
    assert client.patch(f"/api/items/{iid}", json={"condition": "Mint"}).status_code == 200
    _logout(client)

    _login(client, "carol")
    assert client.get(f"/api/items/{iid}").status_code == 200
    assert client.patch(f"/api/items/{iid}", json={"condition": "Poor"}).status_code == 403

"""Tests for the item comment threads feature."""

from __future__ import annotations


def _setup(client, username="alice"):
    """Register, log in, create a collection and an item. Return (collection_id, item_id)."""
    client.post(
        "/api/auth/register",
        json={"username": username, "password": "hunter22-secure", "email": f"{username}@x.io"},
    )
    client.post("/api/auth/login", json={"username": username, "password": "hunter22-secure"})
    cid = client.post("/api/collections", json={"name": "Stuff"}).json()["id"]
    iid = client.post(
        "/api/items",
        json={"collection_id": cid, "category": "tools.hand", "title": "Hammer"},
    ).json()["id"]
    return cid, iid


def _register_and_login(client, username):
    client.post(
        "/api/auth/register",
        json={"username": username, "password": "hunter22-secure", "email": f"{username}@x.io"},
    )
    client.post("/api/auth/login", json={"username": username, "password": "hunter22-secure"})


def test_create_and_list_comment(client) -> None:
    _, iid = _setup(client)
    r = client.post(f"/api/items/{iid}/comments", json={"body": "Great hammer!"})
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["body"] == "Great hammer!"
    assert c["parent_id"] is None
    assert c["author"]["username"] == "alice"

    r2 = client.get(f"/api/items/{iid}/comments")
    assert r2.status_code == 200
    assert len(r2.json()) == 1
    assert r2.json()[0]["id"] == c["id"]


def test_reply_to_comment(client) -> None:
    _, iid = _setup(client)
    parent = client.post(f"/api/items/{iid}/comments", json={"body": "Top level"}).json()
    r = client.post(
        f"/api/items/{iid}/comments",
        json={"body": "Reply here", "parent_id": parent["id"]},
    )
    assert r.status_code == 201
    reply = r.json()
    assert reply["parent_id"] == parent["id"]

    # Top-level list should not include the reply
    top = client.get(f"/api/items/{iid}/comments").json()
    assert len(top) == 1
    assert top[0]["reply_count"] == 1

    # Replies endpoint returns the reply
    replies = client.get(f"/api/items/{iid}/comments/{parent['id']}/replies").json()
    assert len(replies) == 1
    assert replies[0]["id"] == reply["id"]


def test_edit_own_comment(client) -> None:
    _, iid = _setup(client)
    c = client.post(f"/api/items/{iid}/comments", json={"body": "Original"}).json()
    r = client.patch(f"/api/comments/{c['id']}", json={"body": "Updated"})
    assert r.status_code == 200
    assert r.json()["body"] == "Updated"


def test_cannot_edit_others_comment(client) -> None:
    _, iid = _setup(client, "alice2")
    c = client.post(f"/api/items/{iid}/comments", json={"body": "Alice comment"}).json()

    # Bob registers and joins the collection as a member
    _register_and_login(client, "bob2")
    r = client.patch(f"/api/comments/{c['id']}", json={"body": "Bob edit"})
    assert r.status_code == 403


def test_delete_own_comment(client) -> None:
    _, iid = _setup(client)
    c = client.post(f"/api/items/{iid}/comments", json={"body": "Delete me"}).json()
    r = client.delete(f"/api/comments/{c['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/items/{iid}/comments").json() == []


def test_unauthenticated_cannot_comment(client) -> None:
    _, iid = _setup(client)
    from fastapi.testclient import TestClient

    bare = TestClient(client.app)
    r = bare.post(f"/api/items/{iid}/comments", json={"body": "anon"})
    assert r.status_code == 401


def test_comment_not_found(client) -> None:
    _setup(client)
    r = client.patch("/api/comments/nonexistent", json={"body": "x"})
    assert r.status_code == 404


def test_reply_to_nonexistent_parent(client) -> None:
    _, iid = _setup(client)
    r = client.post(
        f"/api/items/{iid}/comments",
        json={"body": "reply", "parent_id": "01FAKEPARENTIDXXXXXXXXXXX"},
    )
    assert r.status_code == 400

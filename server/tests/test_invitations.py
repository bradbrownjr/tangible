"""Invitation lifecycle tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _register(client, username, password="hunter22-secure"):
    r = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    assert r.status_code == 201, r.text


def _login(client, username, password="hunter22-secure"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _logout(client):
    client.post("/auth/logout")


def test_create_and_accept_invitation(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "Movies"}).json()["id"]

    r = client.post(
        f"/collections/{cid}/invitations",
        json={"role": "editor", "email": "bob@x.io"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    token = body["token"]
    assert len(token) >= 32
    assert body["role"] == "editor"
    assert body["accepted_at"] is None
    _logout(client)

    # Anonymous preview works.
    r = client.get(f"/invitations/{token}")
    assert r.status_code == 200
    assert r.json()["collection_name"] == "Movies"
    assert r.json()["role"] == "editor"

    # Bob accepts.
    _login(client, "bob")
    r = client.post(f"/invitations/{token}/accept")
    assert r.status_code == 204

    # Bob can now see the collection.
    r = client.get(f"/collections/{cid}/members")
    assert r.status_code == 200
    assert {m["username"] for m in r.json()} == {"alice", "bob"}


def test_invitation_token_single_use(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    token = client.post(
        f"/collections/{cid}/invitations", json={"role": "viewer"}
    ).json()["token"]
    _logout(client)

    _login(client, "bob")
    assert client.post(f"/invitations/{token}/accept").status_code == 204
    # Already accepted -> 410.
    r = client.post(f"/invitations/{token}/accept")
    assert r.status_code == 410


def test_unknown_token_404(client) -> None:
    r = client.get("/invitations/not-a-token")
    assert r.status_code == 404


def test_expired_invitation(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    token = client.post(
        f"/collections/{cid}/invitations",
        json={"role": "viewer", "expires_at": past},
    ).json()["token"]
    _logout(client)
    assert client.get(f"/invitations/{token}").status_code == 410


def test_revoke_invitation(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    r = client.post(f"/collections/{cid}/invitations", json={"role": "viewer"})
    inv_id = r.json()["id"]
    token = r.json()["token"]
    assert client.delete(
        f"/collections/{cid}/invitations/{inv_id}"
    ).status_code == 204
    _logout(client)
    _login(client, "bob")
    assert client.get(f"/invitations/{token}").status_code == 404


def test_non_owner_cannot_create_invitation(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    _logout(client)
    _login(client, "bob")
    r = client.post(f"/collections/{cid}/invitations", json={"role": "viewer"})
    assert r.status_code == 403


def test_accept_does_not_downgrade_existing_member(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    token = client.post(
        f"/collections/{cid}/invitations", json={"role": "viewer"}
    ).json()["token"]
    _logout(client)
    _login(client, "bob")
    assert client.post(f"/invitations/{token}/accept").status_code == 204
    r = client.get(f"/collections/{cid}/members")
    bob = next(m for m in r.json() if m["username"] == "bob")
    assert bob["role"] == "editor"

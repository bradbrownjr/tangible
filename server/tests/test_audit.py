"""Audit log tests."""

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


def _make_admin(db, username):
    from covet.models import User

    user = db.query(User).filter_by(username=username).one()
    user.is_admin = True
    db.commit()


def test_audit_records_member_add(client, db) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )

    r = client.get(f"/audit?collection_id={cid}")
    assert r.status_code == 200
    actions = [e["action"] for e in r.json()]
    assert "member.add" in actions


def test_audit_records_share_link_lifecycle(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    link_id = client.post(
        f"/collections/{cid}/share-links", json={"label": "ph"}
    ).json()["id"]
    client.delete(f"/collections/{cid}/share-links/{link_id}")
    r = client.get(f"/audit?collection_id={cid}")
    actions = [e["action"] for e in r.json()]
    assert "share_link.create" in actions
    assert "share_link.revoke" in actions


def test_audit_records_invitation_lifecycle(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    token = client.post(
        f"/collections/{cid}/invitations", json={"role": "viewer"}
    ).json()["token"]
    client.post("/auth/logout")
    _login(client, "bob")
    client.post(f"/invitations/{token}/accept")
    client.post("/auth/logout")
    _login(client, "alice")
    r = client.get(f"/audit?collection_id={cid}")
    actions = [e["action"] for e in r.json()]
    assert "invitation.create" in actions
    assert "invitation.accept" in actions


def test_audit_non_owner_403(client) -> None:
    _register(client, "alice")
    _register(client, "bob")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "bob", "role": "editor"},
    )
    client.post("/auth/logout")
    _login(client, "bob")
    r = client.get(f"/audit?collection_id={cid}")
    assert r.status_code == 403


def test_audit_global_requires_admin(client) -> None:
    _register(client, "alice")
    _login(client, "alice")
    r = client.get("/audit")
    assert r.status_code == 403


def test_audit_global_admin_ok(client, db) -> None:
    _register(client, "alice")
    _make_admin(db, "alice")
    _login(client, "alice")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    client.post(f"/collections/{cid}/share-links", json={})
    r = client.get("/audit")
    assert r.status_code == 200
    assert any(e["action"] == "share_link.create" for e in r.json())

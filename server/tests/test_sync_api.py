"""Tests for the CRDT sync relay endpoints.

The server only stores opaque change blobs; these tests use random bytes as
"changes" — they're meaningful only to a real CRDT client.
"""

from __future__ import annotations

import base64
import hashlib
import secrets


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _change(actor: str = "actor-a") -> dict:
    blob = secrets.token_bytes(64)
    return {
        "change_hash": hashlib.sha256(blob).hexdigest(),
        "actor_id": actor,
        "blob_b64": _b64(blob),
    }


def _signup_and_login(client, username: str, password: str = "hunter22-secure") -> None:
    client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _make_collection(client) -> str:
    r = client.post("/api/collections", json={"name": "Sync Test"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_push_and_pull_changes(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    doc_id = "01J0TESTITEMDOC0000000ABCD"  # 26 chars

    c1, c2 = _change(), _change()

    r = client.post(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes",
        json={"changes": [c1, c2]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 2
    assert body["duplicate"] == 0
    assert body["head_seq"] == 2
    assert body["doc_id"] == doc_id

    # Idempotent re-push: both should be duplicates.
    r = client.post(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes",
        json={"changes": [c1, c2]},
    )
    assert r.status_code == 200
    assert r.json() == {
        "doc_id": doc_id,
        "accepted": 0,
        "duplicate": 2,
        "head_seq": 2,
    }

    # Pull from 0: should return both, in order.
    r = client.get(f"/api/collections/{cid}/sync/item/{doc_id}/changes")
    assert r.status_code == 200
    pulled = r.json()
    assert pulled["head_seq"] == 2
    assert pulled["has_more"] is False
    assert [c["server_seq"] for c in pulled["changes"]] == [1, 2]
    assert pulled["changes"][0]["change_hash"] == c1["change_hash"]
    assert pulled["changes"][0]["blob_b64"] == c1["blob_b64"]

    # Incremental pull.
    r = client.get(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes", params={"since": 1}
    )
    assert r.status_code == 200
    assert [c["server_seq"] for c in r.json()["changes"]] == [2]


def test_list_collection_docs(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    doc_a, doc_b = "DOC0000000000000000000001A", "DOC0000000000000000000002B"

    client.post(
        f"/api/collections/{cid}/sync/item/{doc_a}/changes", json={"changes": [_change()]}
    )
    client.post(
        f"/api/collections/{cid}/sync/item/{doc_b}/changes",
        json={"changes": [_change(), _change()]},
    )

    r = client.get(f"/api/collections/{cid}/sync")
    assert r.status_code == 200
    summaries = {s["id"]: s for s in r.json()}
    assert summaries[doc_a]["head_seq"] == 1
    assert summaries[doc_b]["head_seq"] == 2
    assert summaries[doc_a]["has_snapshot"] is False


def test_snapshot_compaction(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    doc_id = "DOC0000000000000000000003C"

    # Push three changes.
    changes = [_change() for _ in range(3)]
    client.post(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes", json={"changes": changes}
    )

    snap_bytes = secrets.token_bytes(128)
    head_hash = hashlib.sha256(snap_bytes).hexdigest()

    # Upload snapshot covering the first two changes.
    r = client.put(
        f"/api/collections/{cid}/sync/item/{doc_id}/snapshot",
        json={
            "snapshot_b64": _b64(snap_bytes),
            "head_hash": head_hash,
            "up_to_server_seq": 2,
        },
    )
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["head_hash"] == head_hash
    assert snap["snapshot_b64"] == _b64(snap_bytes)
    # head_seq remains 3 (one un-compacted change left).
    assert snap["head_seq"] == 3

    # Pulling from 0 now only returns the post-snapshot tail.
    r = client.get(f"/api/collections/{cid}/sync/item/{doc_id}/changes")
    assert r.status_code == 200
    tail = r.json()["changes"]
    assert [c["server_seq"] for c in tail] == [3]

    # Snapshot is fetchable.
    r = client.get(f"/api/collections/{cid}/sync/item/{doc_id}/snapshot")
    assert r.status_code == 200
    assert r.json()["snapshot_b64"] == _b64(snap_bytes)

    # Cannot snapshot beyond head.
    r = client.put(
        f"/api/collections/{cid}/sync/item/{doc_id}/snapshot",
        json={
            "snapshot_b64": _b64(snap_bytes),
            "head_hash": head_hash,
            "up_to_server_seq": 999,
        },
    )
    assert r.status_code == 409


def test_sync_acl(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    doc_id = "DOC0000000000000000000004D"
    client.post(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes", json={"changes": [_change()]}
    )

    # Bob has no access.
    client.post("/api/auth/logout")
    _signup_and_login(client, "bob")
    r = client.get(f"/api/collections/{cid}/sync")
    assert r.status_code == 403
    r = client.get(f"/api/collections/{cid}/sync/item/{doc_id}/changes")
    assert r.status_code == 403
    r = client.post(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes",
        json={"changes": [_change("bob")]},
    )
    assert r.status_code == 403


def test_invalid_blob_rejected(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    doc_id = "DOC0000000000000000000005E"

    r = client.post(
        f"/api/collections/{cid}/sync/item/{doc_id}/changes",
        json={
            "changes": [
                {"change_hash": "abc", "actor_id": "x", "blob_b64": "!!!not base64!!!"}
            ]
        },
    )
    assert r.status_code == 400


def test_pull_unknown_doc_404(client) -> None:
    _signup_and_login(client, "alice")
    cid = _make_collection(client)
    r = client.get(f"/api/collections/{cid}/sync/item/DOCNOPE000000000000000NOPE/changes")
    assert r.status_code == 404

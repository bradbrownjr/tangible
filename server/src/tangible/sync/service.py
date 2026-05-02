"""CRDT sync relay service.

Server-side semantics:

* The server treats CRDT change blobs as opaque bytes — it does not parse,
  apply, or merge them. Real CRDT logic (Automerge) lives in clients.
* For each (collection, kind, doc_id) we maintain an :class:`AutomergeDoc`
  row plus an append-only log of :class:`AutomergeChange` rows.
* ``server_seq`` is a per-doc monotonically increasing integer assigned at
  insert time. Clients pull with ``?since=N`` to receive the tail.
* Pushes are idempotent on ``(doc_id, change_hash)``: re-uploading the same
  change is silently ignored (counted as ``duplicate``).
* Snapshots may be uploaded by clients; the server stores the latest one and
  may compact old change rows whose ``server_seq <= up_to_server_seq``.
"""

from __future__ import annotations

import base64
import binascii

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DBSession

from tangible.models.sync_doc import AutomergeChange, AutomergeDoc
from tangible.schemas.sync import (
    SyncChange,
    SyncChangeUpload,
    SyncDocSummary,
    SyncPullResponse,
    SyncPushResponse,
    SyncSnapshotResponse,
    SyncSnapshotUpload,
)

MAX_BLOB_BYTES = 256 * 1024  # 256 KiB per individual change
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024  # 8 MiB per snapshot
DEFAULT_PULL_LIMIT = 200


class SyncError(ValueError):
    """Raised for client-input errors (decoded by the API layer to 400/413)."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _decode_b64(value: str, *, max_bytes: int, field: str) -> bytes:
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SyncError(f"{field}: invalid base64") from exc
    if len(raw) > max_bytes:
        raise SyncError(
            f"{field}: payload exceeds {max_bytes} bytes",
            status_code=413,
        )
    if len(raw) == 0:
        raise SyncError(f"{field}: payload must not be empty")
    return raw


def _get_or_create_doc(
    db: DBSession, *, collection_id: str, kind: str, doc_id: str
) -> AutomergeDoc:
    doc = db.get(AutomergeDoc, doc_id)
    if doc is None:
        doc = AutomergeDoc(id=doc_id, collection_id=collection_id, kind=kind)
        db.add(doc)
        db.flush()
    elif doc.collection_id != collection_id:
        raise SyncError(
            "doc_id belongs to a different collection",
            status_code=409,
        )
    elif doc.kind != kind:
        raise SyncError("doc_id belongs to a different kind", status_code=409)
    return doc


def _head_seq(db: DBSession, doc_id: str) -> int:
    value = db.scalar(
        select(func.coalesce(func.max(AutomergeChange.server_seq), 0)).where(
            AutomergeChange.doc_id == doc_id
        )
    )
    return int(value or 0)


def list_docs(db: DBSession, *, collection_id: str) -> list[SyncDocSummary]:
    docs = db.scalars(
        select(AutomergeDoc).where(AutomergeDoc.collection_id == collection_id)
    ).all()
    summaries: list[SyncDocSummary] = []
    for doc in docs:
        summaries.append(
            SyncDocSummary(
                id=doc.id,
                kind=doc.kind,
                head_seq=_head_seq(db, doc.id),
                head_hash=doc.head_hash,
                has_snapshot=doc.snapshot is not None,
                updated_at=doc.updated_at,
            )
        )
    return summaries


def push_changes(
    db: DBSession,
    *,
    collection_id: str,
    kind: str,
    doc_id: str,
    changes: list[SyncChangeUpload],
) -> SyncPushResponse:
    doc = _get_or_create_doc(
        db, collection_id=collection_id, kind=kind, doc_id=doc_id
    )

    accepted = 0
    duplicate = 0
    next_seq = _head_seq(db, doc.id)
    last_hash: str | None = None

    if changes:
        existing_hashes = set(
            db.scalars(
                select(AutomergeChange.change_hash).where(
                    AutomergeChange.doc_id == doc.id,
                    AutomergeChange.change_hash.in_([c.change_hash for c in changes]),
                )
            ).all()
        )
        for change in changes:
            if change.change_hash in existing_hashes:
                duplicate += 1
                continue
            blob = _decode_b64(
                change.blob_b64, max_bytes=MAX_BLOB_BYTES, field="blob_b64"
            )
            next_seq += 1
            db.add(
                AutomergeChange(
                    doc_id=doc.id,
                    server_seq=next_seq,
                    change_hash=change.change_hash,
                    actor_id=change.actor_id,
                    blob=blob,
                )
            )
            existing_hashes.add(change.change_hash)
            last_hash = change.change_hash
            accepted += 1

    if accepted > 0 and last_hash is not None:
        doc.head_hash = last_hash

    db.commit()
    return SyncPushResponse(
        doc_id=doc.id,
        accepted=accepted,
        duplicate=duplicate,
        head_seq=next_seq,
    )


def pull_changes(
    db: DBSession,
    *,
    collection_id: str,
    kind: str,
    doc_id: str,
    since: int = 0,
    limit: int = DEFAULT_PULL_LIMIT,
) -> SyncPullResponse | None:
    doc = db.get(AutomergeDoc, doc_id)
    if doc is None:
        return None
    if doc.collection_id != collection_id or doc.kind != kind:
        return None

    limit = max(1, min(limit, 1000))
    rows = db.scalars(
        select(AutomergeChange)
        .where(AutomergeChange.doc_id == doc.id, AutomergeChange.server_seq > since)
        .order_by(AutomergeChange.server_seq.asc())
        .limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    head_seq = _head_seq(db, doc.id)
    return SyncPullResponse(
        doc_id=doc.id,
        kind=doc.kind,
        head_seq=head_seq,
        changes=[
            SyncChange(
                server_seq=row.server_seq,
                change_hash=row.change_hash,
                actor_id=row.actor_id,
                blob_b64=base64.b64encode(row.blob).decode("ascii"),
            )
            for row in rows
        ],
        has_more=has_more,
    )


def put_snapshot(
    db: DBSession,
    *,
    collection_id: str,
    kind: str,
    doc_id: str,
    payload: SyncSnapshotUpload,
) -> SyncSnapshotResponse:
    doc = _get_or_create_doc(
        db, collection_id=collection_id, kind=kind, doc_id=doc_id
    )
    snapshot = _decode_b64(
        payload.snapshot_b64, max_bytes=MAX_SNAPSHOT_BYTES, field="snapshot_b64"
    )

    head_seq = _head_seq(db, doc.id)
    if payload.up_to_server_seq > head_seq:
        raise SyncError(
            f"up_to_server_seq ({payload.up_to_server_seq}) exceeds head ({head_seq})",
            status_code=409,
        )

    doc.snapshot = snapshot
    doc.head_hash = payload.head_hash

    if payload.up_to_server_seq > 0:
        db.execute(
            delete(AutomergeChange).where(
                AutomergeChange.doc_id == doc.id,
                AutomergeChange.server_seq <= payload.up_to_server_seq,
            )
        )
    db.commit()

    return SyncSnapshotResponse(
        doc_id=doc.id,
        head_seq=_head_seq(db, doc.id),
        head_hash=doc.head_hash,
        snapshot_b64=base64.b64encode(doc.snapshot).decode("ascii")
        if doc.snapshot
        else None,
    )


def get_snapshot(
    db: DBSession, *, collection_id: str, kind: str, doc_id: str
) -> SyncSnapshotResponse | None:
    doc = db.get(AutomergeDoc, doc_id)
    if doc is None or doc.collection_id != collection_id or doc.kind != kind:
        return None
    return SyncSnapshotResponse(
        doc_id=doc.id,
        head_seq=_head_seq(db, doc.id),
        head_hash=doc.head_hash,
        snapshot_b64=base64.b64encode(doc.snapshot).decode("ascii")
        if doc.snapshot
        else None,
    )


__all__ = [
    "MAX_BLOB_BYTES",
    "MAX_SNAPSHOT_BYTES",
    "SyncError",
    "get_snapshot",
    "list_docs",
    "pull_changes",
    "push_changes",
    "put_snapshot",
]

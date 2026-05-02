"""Schemas for the CRDT sync relay.

The server is intentionally CRDT-agnostic: it stores opaque, base64-encoded
change blobs (and optional snapshots) on behalf of clients (web, Android),
which run a real CRDT implementation (Automerge). The server only assigns a
monotonically increasing ``server_seq`` per (doc) and deduplicates by
``change_hash``.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SyncDocSummary(BaseModel):
    """One row per known CRDT doc in a collection."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    head_seq: int = Field(
        description="Highest server_seq currently stored for this doc (0 if no changes yet)"
    )
    head_hash: str | None = None
    has_snapshot: bool = False
    updated_at: datetime


class SyncChange(BaseModel):
    """A single CRDT change. ``blob`` is base64-encoded raw bytes."""

    server_seq: int
    change_hash: str = Field(min_length=1, max_length=64)
    actor_id: str = Field(min_length=1, max_length=64)
    blob_b64: str


class SyncChangeUpload(BaseModel):
    """A single change pushed by a client (no server_seq yet)."""

    change_hash: str = Field(min_length=1, max_length=64)
    actor_id: str = Field(min_length=1, max_length=64)
    blob_b64: str


class SyncPushRequest(BaseModel):
    """Push a batch of changes to a doc. Idempotent on (doc_id, change_hash)."""

    changes: list[SyncChangeUpload] = Field(default_factory=list, max_length=500)


class SyncPushResponse(BaseModel):
    doc_id: str
    accepted: int = Field(description="Number of new changes persisted")
    duplicate: int = Field(description="Number of changes ignored as duplicates")
    head_seq: int


class SyncPullResponse(BaseModel):
    doc_id: str
    kind: str
    head_seq: int
    changes: list[SyncChange]
    has_more: bool = False


class SyncSnapshotUpload(BaseModel):
    """Replace the stored snapshot for a doc.

    ``up_to_server_seq`` declares the inclusive ``server_seq`` represented by
    this snapshot. The server may compact away change rows with
    ``server_seq <= up_to_server_seq`` after persisting the snapshot.
    """

    snapshot_b64: str
    head_hash: str = Field(min_length=1, max_length=64)
    up_to_server_seq: int = Field(ge=0)


class SyncSnapshotResponse(BaseModel):
    doc_id: str
    head_seq: int
    head_hash: str | None
    snapshot_b64: str | None


__all__ = [
    "SyncChange",
    "SyncChangeUpload",
    "SyncDocSummary",
    "SyncPullResponse",
    "SyncPushRequest",
    "SyncPushResponse",
    "SyncSnapshotResponse",
    "SyncSnapshotUpload",
]

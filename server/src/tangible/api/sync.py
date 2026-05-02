"""CRDT sync endpoints.

All routes are nested under ``/collections/{collection_id}/sync`` so that
collection-level RBAC applies uniformly:

* viewer+: list docs, pull changes, fetch snapshot
* editor+: push changes, upload snapshot
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, require_collection_role
from tangible.db import get_session
from tangible.schemas.sync import (
    SyncDocSummary,
    SyncPullResponse,
    SyncPushRequest,
    SyncPushResponse,
    SyncSnapshotResponse,
    SyncSnapshotUpload,
)
from tangible.sync import service as sync_service
from tangible.sync.service import DEFAULT_PULL_LIMIT, SyncError

router = APIRouter(prefix="/collections/{collection_id}/sync", tags=["sync"])


def _wrap_sync_error(exc: SyncError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("", response_model=list[SyncDocSummary])
def list_collection_docs(
    collection_id: str = Path(...),
    db: DBSession = Depends(get_session),
    _auth: AuthContext = Depends(require_collection_role("viewer")),
) -> list[SyncDocSummary]:
    return sync_service.list_docs(db, collection_id=collection_id)


@router.post(
    "/{kind}/{doc_id}/changes",
    response_model=SyncPushResponse,
    status_code=status.HTTP_200_OK,
)
def push_doc_changes(
    payload: SyncPushRequest,
    collection_id: str = Path(...),
    kind: str = Path(..., min_length=1, max_length=32),
    doc_id: str = Path(..., min_length=1, max_length=26),
    db: DBSession = Depends(get_session),
    _auth: AuthContext = Depends(require_collection_role("editor")),
) -> SyncPushResponse:
    try:
        return sync_service.push_changes(
            db,
            collection_id=collection_id,
            kind=kind,
            doc_id=doc_id,
            changes=payload.changes,
        )
    except SyncError as exc:
        raise _wrap_sync_error(exc) from exc


@router.get(
    "/{kind}/{doc_id}/changes",
    response_model=SyncPullResponse,
)
def pull_doc_changes(
    collection_id: str = Path(...),
    kind: str = Path(..., min_length=1, max_length=32),
    doc_id: str = Path(..., min_length=1, max_length=26),
    since: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PULL_LIMIT, ge=1, le=1000),
    db: DBSession = Depends(get_session),
    _auth: AuthContext = Depends(require_collection_role("viewer")),
) -> SyncPullResponse:
    result = sync_service.pull_changes(
        db,
        collection_id=collection_id,
        kind=kind,
        doc_id=doc_id,
        since=since,
        limit=limit,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doc not found")
    return result


@router.put(
    "/{kind}/{doc_id}/snapshot",
    response_model=SyncSnapshotResponse,
)
def put_doc_snapshot(
    payload: SyncSnapshotUpload,
    collection_id: str = Path(...),
    kind: str = Path(..., min_length=1, max_length=32),
    doc_id: str = Path(..., min_length=1, max_length=26),
    db: DBSession = Depends(get_session),
    _auth: AuthContext = Depends(require_collection_role("editor")),
) -> SyncSnapshotResponse:
    try:
        return sync_service.put_snapshot(
            db,
            collection_id=collection_id,
            kind=kind,
            doc_id=doc_id,
            payload=payload,
        )
    except SyncError as exc:
        raise _wrap_sync_error(exc) from exc


@router.get(
    "/{kind}/{doc_id}/snapshot",
    response_model=SyncSnapshotResponse,
)
def get_doc_snapshot(
    collection_id: str = Path(...),
    kind: str = Path(..., min_length=1, max_length=32),
    doc_id: str = Path(..., min_length=1, max_length=26),
    db: DBSession = Depends(get_session),
    _auth: AuthContext = Depends(require_collection_role("viewer")),
) -> SyncSnapshotResponse:
    result = sync_service.get_snapshot(
        db, collection_id=collection_id, kind=kind, doc_id=doc_id
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doc not found")
    return result

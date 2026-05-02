"""Document attachment endpoints."""

from __future__ import annotations

import hashlib
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from tangible.config import get_settings
from tangible.db import get_session
from tangible.models import Document, Item
from tangible.schemas import DocumentRead, DocumentUpdate
from tangible.services.document_search import extract_search_text

router = APIRouter(tags=["documents"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}

_ALLOWED_MIME_PREFIXES = (
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/msword",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-excel",
    "text/",
    "image/",
)


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _doc_storage_path(sha256: str) -> Path:
    base = get_settings().documents_dir
    assert base is not None
    p = base / sha256[0:2] / sha256[2:4] / sha256
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _check_mime(mime: str) -> None:
    mime_l = mime.lower()
    if not any(mime_l.startswith(prefix) for prefix in _ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported document type: {mime}",
        )


@router.get("/items/{item_id}/documents", response_model=list[DocumentRead])
def list_documents(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[DocumentRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(Document).where(Document.item_id == item_id).order_by(Document.created_at)
    ).all()
    return [DocumentRead.model_validate(r) for r in rows]


@router.post(
    "/items/{item_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    item_id: str,
    file: UploadFile = File(...),
    label: str | None = Form(default=None, max_length=128),
    category: str | None = Form(default=None, max_length=32),
    expires_at: datetime | None = Form(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> DocumentRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)

    mime = file.content_type or "application/octet-stream"
    _check_mime(mime)

    settings = get_settings()
    max_bytes = settings.documents_max_bytes
    digest = hashlib.sha256()
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds {max_bytes} bytes",
            )
        digest.update(chunk)
        chunks.append(chunk)
    sha256 = digest.hexdigest()

    path = _doc_storage_path(sha256)
    if not path.exists():
        path.write_bytes(b"".join(chunks))

    doc = Document(
        item_id=item_id,
        storage_key=sha256,
        sha256=sha256,
        mime_type=mime,
        byte_size=total,
        filename=file.filename or sha256,
        search_text=extract_search_text(path, mime, file.filename or sha256),
        label=label,
        category=category,
        expires_at=expires_at,
        uploaded_by=auth.user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return DocumentRead.model_validate(doc)


@router.patch("/documents/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: str,
    payload: DocumentUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> DocumentRead:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, doc.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(doc, k, v)
    db.commit()
    db.refresh(doc)
    return DocumentRead.model_validate(doc)


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> FileResponse:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, doc.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    path = _doc_storage_path(doc.sha256)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Document file is missing"
        )
    return FileResponse(
        path,
        media_type=doc.mime_type,
        filename=doc.filename,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, doc.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    sha = doc.sha256
    db.delete(doc)
    db.commit()
    # Garbage-collect file when no remaining references.
    still_used = db.scalar(
        select(Document.id).where(Document.sha256 == sha).limit(1)
    )
    if not still_used:
        path = _doc_storage_path(sha)
        if path.exists():
            with suppress(OSError):
                path.unlink()


# ---------------------------------------------------------------------------
# Expiry dashboard (Phase 9.4)
# ---------------------------------------------------------------------------


@router.get("/expiring", response_model=list[dict])
def list_expiring(
    within_days: int = Query(default=90, ge=1, le=3650),
    collection_id: str | None = Query(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[dict]:
    """Items + documents with ``expires_at`` within the given window."""
    from datetime import UTC, timedelta

    now = datetime.now(UTC)
    horizon = now + timedelta(days=within_days)

    # Restrict to collections the user can read.
    item_q = select(Item).where(Item.expires_at.isnot(None), Item.expires_at <= horizon)
    if collection_id is not None:
        _require_role(db, auth, collection_id, _VIEWER_ROLES)
        item_q = item_q.where(Item.collection_id == collection_id)
    items = db.scalars(item_q).all()

    doc_q = select(Document).where(
        Document.expires_at.isnot(None), Document.expires_at <= horizon
    )
    docs = db.scalars(doc_q).all()

    out: list[dict] = []
    for it in items:
        if collection_role(db, auth.user, it.collection_id) is None:
            continue
        out.append({
            "kind": "item",
            "id": it.id,
            "collection_id": it.collection_id,
            "title": it.title,
            "expires_at": it.expires_at,
        })
    for d in docs:
        item = db.get(Item, d.item_id)
        if item is None:
            continue
        if collection_id is not None and item.collection_id != collection_id:
            continue
        if collection_role(db, auth.user, item.collection_id) is None:
            continue
        out.append({
            "kind": "document",
            "id": d.id,
            "item_id": d.item_id,
            "collection_id": item.collection_id,
            "filename": d.filename,
            "category": d.category,
            "expires_at": d.expires_at,
        })
    out.sort(key=lambda r: r["expires_at"] or now)
    return out

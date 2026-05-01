"""Manual / asset bundle endpoints.

Bundles are reusable manual libraries scoped to a collection. They hold a
set of binary assets (PDFs, diagrams, firmware) and can be linked to many
items via `bundle_items`.
"""

from __future__ import annotations

import hashlib
from contextlib import suppress
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, collection_role, require_user
from covet.config import get_settings
from covet.db import get_session
from covet.models import Item
from covet.models.manual_bundle import (
    BUNDLE_ASSET_KINDS,
    BundleAsset,
    BundleItem,
    ManualBundle,
)
from covet.schemas.manual_bundle import (
    BundleAssetRead,
    BundleAssetUpdate,
    ManualBundleCreate,
    ManualBundleRead,
    ManualBundleUpdate,
)

router = APIRouter(tags=["bundles"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}

_ALLOWED_MIME_PREFIXES = (
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",  # firmware blobs
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


def _asset_storage_path(sha256: str) -> Path:
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
            detail=f"Unsupported asset type: {mime}",
        )


def _load_bundle(db: DBSession, bundle_id: str) -> ManualBundle:
    bundle = db.get(ManualBundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found")
    return bundle


def _serialize(db: DBSession, bundle: ManualBundle) -> ManualBundleRead:
    item_ids = list(
        db.scalars(
            select(BundleItem.item_id).where(BundleItem.bundle_id == bundle.id)
        ).all()
    )
    out = ManualBundleRead.model_validate(bundle)
    out.item_ids = item_ids
    return out


# ---------------------------------------------------------------------------
# Bundle CRUD
# ---------------------------------------------------------------------------


@router.get("/collections/{collection_id}/bundles", response_model=list[ManualBundleRead])
def list_bundles(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ManualBundleRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(ManualBundle)
        .where(ManualBundle.collection_id == collection_id)
        .order_by(ManualBundle.title)
    ).all()
    return [_serialize(db, b) for b in rows]


@router.post(
    "/collections/{collection_id}/bundles",
    response_model=ManualBundleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_bundle(
    collection_id: str,
    payload: ManualBundleCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ManualBundleRead:
    _require_role(db, auth, collection_id, _EDITOR_ROLES)
    bundle = ManualBundle(
        collection_id=collection_id,
        title=payload.title,
        description=payload.description,
        created_by=auth.user.id,
    )
    db.add(bundle)
    db.commit()
    db.refresh(bundle)
    return _serialize(db, bundle)


@router.get("/bundles/{bundle_id}", response_model=ManualBundleRead)
def get_bundle(
    bundle_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ManualBundleRead:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _VIEWER_ROLES)
    return _serialize(db, bundle)


@router.patch("/bundles/{bundle_id}", response_model=ManualBundleRead)
def update_bundle(
    bundle_id: str,
    payload: ManualBundleUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ManualBundleRead:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    updates = payload.model_dump(exclude_unset=True)
    if "primary_asset_id" in updates and updates["primary_asset_id"] is not None:
        asset = db.get(BundleAsset, updates["primary_asset_id"])
        if asset is None or asset.bundle_id != bundle.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="primary_asset_id must reference an asset in this bundle",
            )
    for k, v in updates.items():
        setattr(bundle, k, v)
    db.commit()
    db.refresh(bundle)
    return _serialize(db, bundle)


@router.delete("/bundles/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bundle(
    bundle_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    sha_list = [a.sha256 for a in bundle.assets]
    db.delete(bundle)
    db.commit()
    # GC files no longer referenced by any document or asset.
    for sha in sha_list:
        still_used = db.scalar(
            select(BundleAsset.id).where(BundleAsset.sha256 == sha).limit(1)
        )
        if still_used:
            continue
        from covet.models import Document

        still_used_doc = db.scalar(
            select(Document.id).where(Document.sha256 == sha).limit(1)
        )
        if still_used_doc:
            continue
        path = _asset_storage_path(sha)
        if path.exists():
            with suppress(OSError):
                path.unlink()


# ---------------------------------------------------------------------------
# Asset upload / download / update / delete
# ---------------------------------------------------------------------------


@router.post(
    "/bundles/{bundle_id}/assets",
    response_model=BundleAssetRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    bundle_id: str,
    file: UploadFile = File(...),
    label: str | None = Form(default=None, max_length=128),
    kind: str = Form(default="other", max_length=32),
    sort_order: int = Form(default=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> BundleAssetRead:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    if kind not in BUNDLE_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"kind must be one of {BUNDLE_ASSET_KINDS}",
        )

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

    path = _asset_storage_path(sha256)
    if not path.exists():
        path.write_bytes(b"".join(chunks))

    asset = BundleAsset(
        bundle_id=bundle_id,
        storage_key=sha256,
        sha256=sha256,
        mime_type=mime,
        byte_size=total,
        filename=file.filename or sha256,
        label=label,
        kind=kind,
        sort_order=sort_order,
        uploaded_by=auth.user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return BundleAssetRead.model_validate(asset)


@router.patch("/bundles/{bundle_id}/assets/{asset_id}", response_model=BundleAssetRead)
def update_asset(
    bundle_id: str,
    asset_id: str,
    payload: BundleAssetUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> BundleAssetRead:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    asset = db.get(BundleAsset, asset_id)
    if asset is None or asset.bundle_id != bundle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    updates = payload.model_dump(exclude_unset=True)
    if "kind" in updates and updates["kind"] not in BUNDLE_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"kind must be one of {BUNDLE_ASSET_KINDS}",
        )
    for k, v in updates.items():
        setattr(asset, k, v)
    db.commit()
    db.refresh(asset)
    return BundleAssetRead.model_validate(asset)


@router.get("/bundles/{bundle_id}/assets/{asset_id}/download")
def download_asset(
    bundle_id: str,
    asset_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> FileResponse:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _VIEWER_ROLES)
    asset = db.get(BundleAsset, asset_id)
    if asset is None or asset.bundle_id != bundle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    path = _asset_storage_path(asset.sha256)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Asset file is missing"
        )
    return FileResponse(path, media_type=asset.mime_type, filename=asset.filename)


@router.delete(
    "/bundles/{bundle_id}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset(
    bundle_id: str,
    asset_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    asset = db.get(BundleAsset, asset_id)
    if asset is None or asset.bundle_id != bundle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    sha = asset.sha256
    if bundle.primary_asset_id == asset.id:
        bundle.primary_asset_id = None
    db.delete(asset)
    db.commit()
    still_used = db.scalar(
        select(BundleAsset.id).where(BundleAsset.sha256 == sha).limit(1)
    )
    if still_used:
        return
    from covet.models import Document

    still_used_doc = db.scalar(
        select(Document.id).where(Document.sha256 == sha).limit(1)
    )
    if still_used_doc:
        return
    path = _asset_storage_path(sha)
    if path.exists():
        with suppress(OSError):
            path.unlink()


# ---------------------------------------------------------------------------
# Bundle <-> Item linking
# ---------------------------------------------------------------------------


@router.post(
    "/bundles/{bundle_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def link_item(
    bundle_id: str,
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.collection_id != bundle.collection_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item must be in the same collection as the bundle",
        )
    existing = db.get(BundleItem, {"bundle_id": bundle_id, "item_id": item_id})
    if existing is not None:
        return
    db.add(BundleItem(bundle_id=bundle_id, item_id=item_id))
    db.commit()


@router.delete(
    "/bundles/{bundle_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlink_item(
    bundle_id: str,
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    bundle = _load_bundle(db, bundle_id)
    _require_role(db, auth, bundle.collection_id, _EDITOR_ROLES)
    link = db.get(BundleItem, {"bundle_id": bundle_id, "item_id": item_id})
    if link is None:
        return
    db.delete(link)
    db.commit()


@router.get("/items/{item_id}/bundles", response_model=list[ManualBundleRead])
def list_item_bundles(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ManualBundleRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    bundle_ids = db.scalars(
        select(BundleItem.bundle_id).where(BundleItem.item_id == item_id)
    ).all()
    if not bundle_ids:
        return []
    rows = db.scalars(
        select(ManualBundle).where(ManualBundle.id.in_(bundle_ids)).order_by(ManualBundle.title)
    ).all()
    return [_serialize(db, b) for b in rows]

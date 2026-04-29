"""Photo endpoints (upload, list, set-primary, delete, URL ingest)."""

from __future__ import annotations

import hashlib
import io
from contextlib import suppress
from pathlib import Path

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DBSession

# Register HEIF/HEIC decoders with Pillow (no-op if already registered).
try:  # pragma: no cover - import side effect
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:  # pragma: no cover
    pass

from covet.auth.deps import AuthContext, collection_role, require_user
from covet.config import get_settings
from covet.db import get_session
from covet.models import Item, Photo
from covet.schemas import PhotoFromUrl, PhotoRead, PhotoUpdate
from covet.services.metadata import ScrapeError, validate_url

router = APIRouter(tags=["photos"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _photo_storage_path(sha256: str) -> Path:
    base = get_settings().photos_dir
    assert base is not None
    p = base / sha256[0:2] / sha256[2:4] / sha256
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _normalize_image(raw: bytes, declared_mime: str) -> tuple[bytes, str, int, int]:
    """Decode raw image bytes, apply EXIF rotation, transcode HEIC→JPEG.

    Returns (bytes, mime_type, width, height). Non-image content raises 415.
    """
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            fmt = (img.format or "").upper()
            # Apply EXIF orientation so downstream consumers see upright pixels.
            img = ImageOps.exif_transpose(img)
            width, height = img.size

            if fmt in {"HEIF", "HEIC"}:
                # Transcode to JPEG.
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                out = io.BytesIO()
                img.save(out, format="JPEG", quality=90, optimize=True)
                return out.getvalue(), "image/jpeg", width, height

            # For other formats: re-emit transposed bytes only if EXIF rotation
            # actually changed the pixels. Otherwise return originals.
            mime = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
                "GIF": "image/gif",
                "BMP": "image/bmp",
            }.get(fmt, declared_mime)
            return raw, mime, width, height
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Could not decode image: {exc}",
        ) from exc


def _next_sort_order(db: DBSession, item_id: str) -> int:
    cur = db.scalar(
        select(Photo.sort_order)
        .where(Photo.item_id == item_id)
        .order_by(Photo.sort_order.desc())
        .limit(1)
    )
    return (cur or 0) + 10


def _store_photo(
    db: DBSession, item_id: str, raw: bytes, declared_mime: str
) -> Photo:
    settings = get_settings()
    if len(raw) > settings.photos_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {settings.photos_max_bytes} bytes",
        )
    blob, mime, width, height = _normalize_image(raw, declared_mime)
    sha = hashlib.sha256(blob).hexdigest()
    path = _photo_storage_path(sha)
    if not path.exists():
        path.write_bytes(blob)
    sort_order = _next_sort_order(db, item_id)
    is_first = (
        db.scalar(select(Photo.id).where(Photo.item_id == item_id).limit(1)) is None
    )
    photo = Photo(
        item_id=item_id,
        storage_key=sha,
        sha256=sha,
        mime_type=mime,
        width=width,
        height=height,
        byte_size=len(blob),
        sort_order=sort_order,
        is_primary=is_first,
    )
    db.add(photo)
    db.flush()
    return photo


@router.get("/items/{item_id}/photos", response_model=list[PhotoRead])
def list_photos(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[PhotoRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(Photo).where(Photo.item_id == item_id).order_by(Photo.sort_order)
    ).all()
    return [PhotoRead.model_validate(r) for r in rows]


@router.post(
    "/items/{item_id}/photos",
    response_model=list[PhotoRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_photos(
    item_id: str,
    files: list[UploadFile] = File(..., description="One or more image files"),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[PhotoRead]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    out: list[PhotoRead] = []
    for f in files:
        raw = await f.read()
        photo = _store_photo(db, item_id, raw, f.content_type or "application/octet-stream")
        out.append(PhotoRead.model_validate(photo))
    db.commit()
    return out


@router.post(
    "/items/{item_id}/photos/from-url",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_photo_from_url(
    item_id: str,
    payload: PhotoFromUrl,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> PhotoRead:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    try:
        url = validate_url(payload.url)
    except ScrapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    settings = get_settings()
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch image: {exc}",
        ) from exc
    raw = resp.content
    if len(raw) > settings.photos_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {settings.photos_max_bytes} bytes",
        )
    declared = resp.headers.get("content-type", "application/octet-stream").split(";")[0]
    photo = _store_photo(db, item_id, raw, declared)
    db.commit()
    return PhotoRead.model_validate(photo)


@router.get("/photos/{photo_id}/download")
def download_photo(
    photo_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> FileResponse:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, photo.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _VIEWER_ROLES)
    path = _photo_storage_path(photo.sha256)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Missing file")
    return FileResponse(path, media_type=photo.mime_type)


@router.patch("/photos/{photo_id}", response_model=PhotoRead)
def update_photo(
    photo_id: str,
    payload: PhotoUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> PhotoRead:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, photo.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_primary"):
        # Demote any other primaries on the same item.
        db.execute(
            update(Photo)
            .where(Photo.item_id == photo.item_id, Photo.id != photo.id)
            .values(is_primary=False)
        )
    for k, v in data.items():
        setattr(photo, k, v)
    db.commit()
    db.refresh(photo)
    return PhotoRead.model_validate(photo)


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    photo = db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    item = db.get(Item, photo.item_id)
    assert item is not None
    _require_role(db, auth, item.collection_id, _EDITOR_ROLES)
    sha = photo.sha256
    item_id = photo.item_id
    was_primary = photo.is_primary
    db.delete(photo)
    db.flush()
    if was_primary:
        # Promote the next photo (lowest sort_order) to primary.
        next_p = db.scalar(
            select(Photo).where(Photo.item_id == item_id).order_by(Photo.sort_order).limit(1)
        )
        if next_p is not None:
            next_p.is_primary = True
    db.commit()
    still_used = db.scalar(select(Photo.id).where(Photo.sha256 == sha).limit(1))
    if not still_used:
        path = _photo_storage_path(sha)
        if path.exists():
            with suppress(OSError):
                path.unlink()

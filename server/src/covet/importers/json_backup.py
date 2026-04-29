"""JSON backup / restore for a single user's data.

Scope:
    * collections owned by the user (memberships preserved by username)
    * items + photos (metadata only — photo bytes live on disk and are
      backed up separately; see ``backup_photos`` in the CLI)
    * tags + tag→item links
    * contacts + loans
    * share links

Excluded (server-only): sessions, API tokens, OIDC identities, user table.

Format: a single JSON object with version + payload sections. Restore is
**additive** — IDs are re-keyed to fresh ULIDs on import to avoid clobbering
existing data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import IO, Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.models import (
    Collection,
    Contact,
    Item,
    Loan,
    Photo,
    ShareLink,
    Tag,
    User,
)
from covet.models.base import ulid_str
from covet.models.tag import ItemTag

BACKUP_VERSION = 1


def _serialize(value: Any) -> Any:
    """JSON-safe conversion (datetimes → isoformat, Decimal → float)."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        # Decimal, etc.
        if hasattr(value, "as_tuple"):
            return float(value)
    except Exception:  # pragma: no cover - defensive
        pass
    return value


def _model_to_dict(obj, fields: list[str]) -> dict[str, Any]:
    return {f: _serialize(getattr(obj, f)) for f in fields}


_COLLECTION_FIELDS = ["id", "name", "description", "icon", "is_public"]
_ITEM_FIELDS = [
    "id",
    "collection_id",
    "title",
    "subtitle",
    "notes",
    "condition",
    "quantity",
    "purchase_price",
    "current_value",
    "currency",
    "acquired_at",
    "location",
    "identifiers",
    "attrs",
]
_PHOTO_FIELDS = [
    "id",
    "item_id",
    "storage_key",
    "sha256",
    "mime_type",
    "width",
    "height",
    "byte_size",
    "sort_order",
]
_TAG_FIELDS = ["id", "name", "color"]
_CONTACT_FIELDS = ["id", "name", "email", "phone", "notes"]
_LOAN_FIELDS = ["id", "item_id", "contact_id", "loaned_at", "due_at", "returned_at", "notes"]
_SHARE_FIELDS = ["id", "collection_id", "slug", "label", "expires_at", "revoked"]


@dataclass
class BackupStats:
    collections: int = 0
    items: int = 0
    photos: int = 0
    tags: int = 0
    contacts: int = 0
    loans: int = 0
    share_links: int = 0


def export_user(db: DBSession, *, user: User) -> dict[str, Any]:
    """Build a JSON-serializable backup payload for ``user``."""
    collections = list(
        db.scalars(select(Collection).where(Collection.owner_id == user.id))
    )
    collection_ids = [c.id for c in collections]

    items = (
        list(db.scalars(select(Item).where(Item.collection_id.in_(collection_ids))))
        if collection_ids
        else []
    )
    item_ids = [i.id for i in items]

    photos = (
        list(db.scalars(select(Photo).where(Photo.item_id.in_(item_ids))))
        if item_ids
        else []
    )
    tags = list(db.scalars(select(Tag).where(Tag.owner_id == user.id)))
    contacts = list(db.scalars(select(Contact).where(Contact.owner_id == user.id)))
    loans = (
        list(db.scalars(select(Loan).where(Loan.item_id.in_(item_ids))))
        if item_ids
        else []
    )
    share_links = (
        list(
            db.scalars(
                select(ShareLink).where(ShareLink.collection_id.in_(collection_ids))
            )
        )
        if collection_ids
        else []
    )

    # Tag links: derive from item.tags relationship (if loaded) — fallback to
    # the association table via a query for portability.
    item_tag_pairs: list[tuple[str, str]] = []
    if item_ids:
        rows = db.execute(
            select(ItemTag.item_id, ItemTag.tag_id).where(ItemTag.item_id.in_(item_ids))
        ).all()
        item_tag_pairs = [(r.item_id, r.tag_id) for r in rows]

    payload: dict[str, Any] = {
        "version": BACKUP_VERSION,
        "exported_for": user.username,
        "collections": [_model_to_dict(c, _COLLECTION_FIELDS) for c in collections],
        "items": [
            {**_model_to_dict(i, _ITEM_FIELDS), "category_slug": i.category.slug}
            for i in items
        ],
        "photos": [_model_to_dict(p, _PHOTO_FIELDS) for p in photos],
        "tags": [_model_to_dict(t, _TAG_FIELDS) for t in tags],
        "item_tags": [{"item_id": i, "tag_id": t} for i, t in item_tag_pairs],
        "contacts": [_model_to_dict(c, _CONTACT_FIELDS) for c in contacts],
        "loans": [_model_to_dict(loan, _LOAN_FIELDS) for loan in loans],
        "share_links": [_model_to_dict(s, _SHARE_FIELDS) for s in share_links],
    }
    return payload


def write_backup(db: DBSession, *, user: User, fp: IO[str]) -> BackupStats:
    payload = export_user(db, user=user)
    json.dump(payload, fp, indent=2, default=_serialize)
    return BackupStats(
        collections=len(payload["collections"]),
        items=len(payload["items"]),
        photos=len(payload["photos"]),
        tags=len(payload["tags"]),
        contacts=len(payload["contacts"]),
        loans=len(payload["loans"]),
        share_links=len(payload["share_links"]),
    )


def import_backup(
    db: DBSession, *, user: User, payload: dict[str, Any]
) -> BackupStats:
    """Restore a backup payload **into ``user``'s account**.

    All IDs are re-keyed to fresh ULIDs so the import never collides with
    existing rows. Returns counts of inserted rows.
    """
    if payload.get("version") != BACKUP_VERSION:
        raise ValueError(f"Unsupported backup version: {payload.get('version')}")

    stats = BackupStats()

    coll_id_map: dict[str, str] = {}
    for raw in payload.get("collections", []):
        new_id = ulid_str()
        coll_id_map[raw["id"]] = new_id
        db.add(
            Collection(
                id=new_id,
                owner_id=user.id,
                name=raw["name"],
                description=raw.get("description"),
                icon=raw.get("icon"),
                is_public=bool(raw.get("is_public", False)),
            )
        )
        stats.collections += 1

    item_id_map: dict[str, str] = {}
    slug_cache: dict[str, str] = {}
    for raw in payload.get("items", []):
        old_cid = raw["collection_id"]
        if old_cid not in coll_id_map:
            continue  # orphan — skip
        slug = raw.get("category_slug") or "other.generic"
        if slug not in slug_cache:
            from covet.services.categories import resolve_slug

            try:
                slug_cache[slug] = resolve_slug(db, slug).id
            except LookupError:
                slug_cache[slug] = resolve_slug(db, "other.generic").id
        new_id = ulid_str()
        item_id_map[raw["id"]] = new_id
        db.add(
            Item(
                id=new_id,
                collection_id=coll_id_map[old_cid],
                category_id=slug_cache[slug],
                title=raw["title"],
                subtitle=raw.get("subtitle"),
                notes=raw.get("notes"),
                condition=raw.get("condition"),
                quantity=int(raw.get("quantity", 1)),
                purchase_price=raw.get("purchase_price"),
                current_value=raw.get("current_value"),
                currency=raw.get("currency"),
                location=raw.get("location"),
                identifiers=raw.get("identifiers", {}) or {},
                attrs=raw.get("attrs", {}) or {},
            )
        )
        stats.items += 1

    for raw in payload.get("photos", []):
        new_iid = item_id_map.get(raw["item_id"])
        if new_iid is None:
            continue
        db.add(
            Photo(
                id=ulid_str(),
                item_id=new_iid,
                storage_key=raw["storage_key"],
                sha256=raw["sha256"],
                mime_type=raw["mime_type"],
                width=raw.get("width"),
                height=raw.get("height"),
                byte_size=int(raw["byte_size"]),
                sort_order=int(raw.get("sort_order", 0)),
            )
        )
        stats.photos += 1

    tag_id_map: dict[str, str] = {}
    for raw in payload.get("tags", []):
        new_id = ulid_str()
        tag_id_map[raw["id"]] = new_id
        db.add(Tag(id=new_id, owner_id=user.id, name=raw["name"], color=raw.get("color")))
        stats.tags += 1

    # Link items↔tags via the relationship to avoid hitting the association
    # table directly (keeps SQLAlchemy's session in sync).
    if payload.get("item_tags"):
        db.flush()
        for link in payload["item_tags"]:
            new_iid = item_id_map.get(link["item_id"])
            new_tid = tag_id_map.get(link["tag_id"])
            if new_iid is None or new_tid is None:
                continue
            db.add(ItemTag(item_id=new_iid, tag_id=new_tid))

    contact_id_map: dict[str, str] = {}
    for raw in payload.get("contacts", []):
        new_id = ulid_str()
        contact_id_map[raw["id"]] = new_id
        db.add(
            Contact(
                id=new_id,
                owner_id=user.id,
                name=raw["name"],
                email=raw.get("email"),
                phone=raw.get("phone"),
                notes=raw.get("notes"),
            )
        )
        stats.contacts += 1

    for raw in payload.get("loans", []):
        new_iid = item_id_map.get(raw["item_id"])
        new_cid = contact_id_map.get(raw["contact_id"])
        if new_iid is None or new_cid is None:
            continue
        db.add(
            Loan(
                id=ulid_str(),
                item_id=new_iid,
                contact_id=new_cid,
                loaned_at=raw["loaned_at"],
                due_at=raw.get("due_at"),
                returned_at=raw.get("returned_at"),
                notes=raw.get("notes"),
            )
        )
        stats.loans += 1

    for raw in payload.get("share_links", []):
        new_cid = coll_id_map.get(raw["collection_id"])
        if new_cid is None:
            continue
        db.add(
            ShareLink(
                id=ulid_str(),
                collection_id=new_cid,
                slug=f"{raw['slug']}-{ulid_str()[:6].lower()}",
                label=raw.get("label"),
                expires_at=raw.get("expires_at"),
                revoked=bool(raw.get("revoked", False)),
            )
        )
        stats.share_links += 1

    db.commit()
    return stats


__all__ = ["BACKUP_VERSION", "BackupStats", "export_user", "import_backup", "write_backup"]

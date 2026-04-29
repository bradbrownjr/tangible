"""Helpers for the curated category tree."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.models.category import Category


def resolve_slug(db: DBSession, slug: str) -> Category:
    """Return the Category for a slug, raising LookupError if missing."""
    cat = db.scalars(select(Category).where(Category.slug == slug)).first()
    if cat is None:
        raise LookupError(f"Unknown category slug: {slug}")
    return cat


def slug_to_id(db: DBSession, slug: str) -> str:
    return resolve_slug(db, slug).id


def subtree_ids(db: DBSession, root_slug: str) -> list[str]:
    """Return the ids of ``root_slug`` and all of its direct children."""
    root = resolve_slug(db, root_slug)
    children = db.scalars(
        select(Category.id).where(Category.parent_id == root.id)
    ).all()
    return [root.id, *children]

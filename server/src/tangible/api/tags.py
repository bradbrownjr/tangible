"""Tag endpoints (per-user)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from tangible.auth.deps import AuthContext, require_user
from tangible.db import get_session
from tangible.models import Tag
from tangible.schemas import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


def _build_tag_hierarchy(tag: Tag) -> TagRead:
    """Convert a Tag model to TagRead, including children recursively."""
    children = sorted(tag.children, key=lambda t: t.name)
    return TagRead(
        id=tag.id,
        owner_id=tag.owner_id,
        name=tag.name,
        parent_id=tag.parent_id,
        color=tag.color,
        children=[_build_tag_hierarchy(child) for child in children],
    )


def _validate_parent_assignment(
    db: DBSession, tag_id: str, parent_id: str | None, owner_id: str
) -> None:
    """Validate that a parent assignment is valid (no cycles, ownership check)."""
    if parent_id is None:
        return

    # Check that parent exists and belongs to the same owner
    parent = db.get(Tag, parent_id)
    if parent is None or parent.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parent tag not found or does not belong to this user",
        )

    # Prevent self-referencing
    if tag_id == parent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tag cannot be its own parent",
        )

    # Prevent cycles: walk up the parent chain
    seen: set[str] = set()
    current = parent
    while current is not None:
        if current.id in seen or current.id == tag_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Parent assignment would create a cycle",
            )
        seen.add(current.id)
        current = current.parent


@router.get("", response_model=list[TagRead])
def list_tags(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[TagRead]:
    """List all tags for the authenticated user, organized in a hierarchy."""
    # Get only root-level tags (parent_id is None)
    stmt = (
        select(Tag)
        .where(Tag.owner_id == auth.user.id)
        .where(Tag.parent_id.is_(None))
        .options(selectinload(Tag.children))
        .order_by(Tag.name)
    )
    root_tags = db.scalars(stmt).unique().all()
    return [_build_tag_hierarchy(tag) for tag in sorted(root_tags, key=lambda t: t.name)]


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> TagRead:
    """Create a new tag for the authenticated user."""
    if payload.parent_id is not None:
        _validate_parent_assignment(db, "", payload.parent_id, auth.user.id)

    tag = Tag(owner_id=auth.user.id, **payload.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _build_tag_hierarchy(tag)


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: str,
    payload: TagUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> TagRead:
    """Update an existing tag."""
    tag = db.get(Tag, tag_id)
    if tag is None or tag.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if payload.parent_id != tag.parent_id:
        _validate_parent_assignment(db, tag_id, payload.parent_id, auth.user.id)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tag, key, value)
    db.commit()
    db.refresh(tag)
    return _build_tag_hierarchy(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    """Delete a tag and all its children."""
    tag = db.get(Tag, tag_id)
    if tag is None or tag.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(tag)
    db.commit()

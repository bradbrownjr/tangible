"""Item comment endpoints.

Provides threaded, time-stamped annotations on items beyond the single
``notes`` field.  Comments are collection-scoped: any member can read;
editors and owners can create.  Authors can edit or delete their own
comments; collection owners can delete any comment.

Routes:
    GET  /items/{item_id}/comments
    POST /items/{item_id}/comments
    PATCH  /comments/{comment_id}
    DELETE /comments/{comment_id}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, collection_role, require_user
from covet.db import get_session
from covet.models import Item, ItemComment
from covet.models.base import ulid_str, utcnow

router = APIRouter(tags=["comments"])

_VIEWER_ROLES = {"viewer", "editor", "owner"}
_EDITOR_ROLES = {"editor", "owner"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CommentAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    display_name: str | None = None


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    item_id: str
    parent_id: str | None
    body: str
    created_at: str
    updated_at: str
    author: CommentAuthor
    reply_count: int = 0


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)
    parent_id: str | None = None


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_item_or_404(db: DBSession, item_id: str) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


def _require_collection_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _comment_to_read(comment: ItemComment, db: DBSession) -> CommentRead:
    reply_count = db.scalar(
        select(func.count(ItemComment.id)).where(ItemComment.parent_id == comment.id)
    ) or 0
    return CommentRead(
        id=comment.id,
        item_id=comment.item_id,
        parent_id=comment.parent_id,
        body=comment.body,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat(),
        author=CommentAuthor(
            id=comment.author.id,
            username=comment.author.username,
            display_name=comment.author.display_name,
        ),
        reply_count=reply_count,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/items/{item_id}/comments", response_model=list[CommentRead])
def list_comments(
    item_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[CommentRead]:
    """Return all top-level comments for an item, newest first."""
    item = _get_item_or_404(db, item_id)
    _require_collection_role(db, auth, item.collection_id, _VIEWER_ROLES)

    rows = db.scalars(
        select(ItemComment)
        .where(ItemComment.item_id == item_id, ItemComment.parent_id.is_(None))
        .order_by(ItemComment.created_at.desc())
    ).all()
    return [_comment_to_read(c, db) for c in rows]


@router.get("/items/{item_id}/comments/{parent_id}/replies", response_model=list[CommentRead])
def list_replies(
    item_id: str,
    parent_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[CommentRead]:
    """Return all replies to a specific comment, oldest first."""
    item = _get_item_or_404(db, item_id)
    _require_collection_role(db, auth, item.collection_id, _VIEWER_ROLES)

    rows = db.scalars(
        select(ItemComment)
        .where(ItemComment.item_id == item_id, ItemComment.parent_id == parent_id)
        .order_by(ItemComment.created_at)
    ).all()
    return [_comment_to_read(c, db) for c in rows]


@router.post(
    "/items/{item_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    item_id: str,
    payload: CommentCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> CommentRead:
    """Post a new comment or reply on an item.

    Any collection member can comment (viewer+).  Pass ``parent_id`` to reply
    to an existing comment.
    """
    item = _get_item_or_404(db, item_id)
    _require_collection_role(db, auth, item.collection_id, _VIEWER_ROLES)

    if payload.parent_id is not None:
        parent = db.get(ItemComment, payload.parent_id)
        if parent is None or parent.item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Parent comment not found"
            )

    now = utcnow()
    comment = ItemComment(
        id=ulid_str(),
        item_id=item_id,
        user_id=auth.user.id,
        parent_id=payload.parent_id,
        body=payload.body.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _comment_to_read(comment, db)


@router.patch("/comments/{comment_id}", response_model=CommentRead)
def update_comment(
    comment_id: str,
    payload: CommentUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> CommentRead:
    """Edit a comment body. Only the author can edit their own comments."""
    comment = db.get(ItemComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    item = _get_item_or_404(db, comment.item_id)
    _require_collection_role(db, auth, item.collection_id, _VIEWER_ROLES)

    if comment.user_id != auth.user.id and not auth.user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your comment")

    comment.body = payload.body.strip()
    comment.updated_at = utcnow()
    db.commit()
    db.refresh(comment)
    return _comment_to_read(comment, db)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    """Delete a comment. Authors can delete their own; collection owners can delete any."""
    comment = db.get(ItemComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    item = _get_item_or_404(db, comment.item_id)
    role = collection_role(db, auth.user, item.collection_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    is_author = comment.user_id == auth.user.id
    is_owner_or_admin = role == "owner" or auth.user.is_admin
    if not is_author and not is_owner_or_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db.delete(comment)
    db.commit()

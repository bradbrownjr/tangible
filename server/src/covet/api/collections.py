"""Collection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import (
    AuthContext,
    require_collection_role,
    require_user,
)
from covet.db import get_session
from covet.models import Collection, CollectionMembership, User
from covet.schemas import (
    CollectionCreate,
    CollectionRead,
    CollectionUpdate,
    MembershipCreate,
    MembershipDetail,
    MembershipUpdate,
)

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("", response_model=list[CollectionRead])
def list_collections(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[CollectionRead]:
    stmt = (
        select(Collection)
        .outerjoin(
            CollectionMembership,
            CollectionMembership.collection_id == Collection.id,
        )
        .where(
            or_(
                Collection.owner_id == auth.user.id,
                CollectionMembership.user_id == auth.user.id,
            )
        )
        .distinct()
        .order_by(Collection.name)
    )
    return [CollectionRead.model_validate(c) for c in db.scalars(stmt)]


@router.post("", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: CollectionCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> CollectionRead:
    collection = Collection(owner_id=auth.user.id, **payload.model_dump())
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return CollectionRead.model_validate(collection)


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection(
    collection_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("viewer")),
) -> CollectionRead:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return CollectionRead.model_validate(collection)


@router.patch("/{collection_id}", response_model=CollectionRead)
def update_collection(
    collection_id: str,
    payload: CollectionUpdate,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> CollectionRead:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(collection, key, value)
    db.commit()
    db.refresh(collection)
    return CollectionRead.model_validate(collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> None:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(collection)
    db.commit()


# --- Members --------------------------------------------------------------------------------


def _membership_to_detail(
    membership: CollectionMembership, user: User
) -> MembershipDetail:
    return MembershipDetail(
        id=membership.id,
        collection_id=membership.collection_id,
        user_id=user.id,
        role=membership.role,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
    )


@router.get("/{collection_id}/members", response_model=list[MembershipDetail])
def list_members(
    collection_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("viewer")),
) -> list[MembershipDetail]:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    rows: list[MembershipDetail] = []
    # Owner is implicit (no membership row); surface it first so the UI can
    # render the full member list without a separate request.
    owner = db.get(User, collection.owner_id)
    if owner is not None:
        rows.append(
            MembershipDetail(
                id=f"owner:{owner.id}",
                collection_id=collection_id,
                user_id=owner.id,
                role="owner",
                username=owner.username,
                email=owner.email,
                display_name=owner.display_name,
            )
        )

    stmt = (
        select(CollectionMembership, User)
        .join(User, CollectionMembership.user_id == User.id)
        .where(CollectionMembership.collection_id == collection_id)
        .order_by(User.username)
    )
    for membership, user in db.execute(stmt):
        rows.append(_membership_to_detail(membership, user))
    return rows


@router.post(
    "/{collection_id}/members",
    response_model=MembershipDetail,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    collection_id: str,
    payload: MembershipCreate,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> MembershipDetail:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    ident = payload.user_identifier.strip()
    user = db.scalar(
        select(User).where(or_(User.username == ident, User.email == ident))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.id == collection.owner_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Owner cannot be added as a member"
        )

    existing = db.scalar(
        select(CollectionMembership).where(
            CollectionMembership.collection_id == collection_id,
            CollectionMembership.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this collection",
        )

    membership = CollectionMembership(
        collection_id=collection_id, user_id=user.id, role=payload.role
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _membership_to_detail(membership, user)


@router.patch("/{collection_id}/members/{member_id}", response_model=MembershipDetail)
def update_member(
    collection_id: str,
    member_id: str,
    payload: MembershipUpdate,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> MembershipDetail:
    membership = db.get(CollectionMembership, member_id)
    if membership is None or membership.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    user = db.get(User, membership.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User missing")
    return _membership_to_detail(membership, user)


@router.delete(
    "/{collection_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(
    collection_id: str,
    member_id: str,
    db: DBSession = Depends(get_session),
    _: AuthContext = Depends(require_collection_role("owner")),
) -> None:
    membership = db.get(CollectionMembership, member_id)
    if membership is None or membership.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(membership)
    db.commit()

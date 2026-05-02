"""Collection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import distinct, or_, select
from sqlalchemy.orm import Session as DBSession

from tangible.api.item_templates import _do_scaffold
from tangible.auth.deps import (
    AuthContext,
    collection_role,
    require_collection_role,
    require_user,
)
from tangible.db import get_session
from tangible.models import Collection, CollectionMembership, User
from tangible.schemas import (
    CollectionCreate,
    CollectionRead,
    CollectionUpdate,
    MembershipCreate,
    MembershipDetail,
    MembershipUpdate,
)
from tangible.services import audit
from tangible.services.reports import CollectionReport

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
    db.flush()  # populate collection.id before scaffolding
    _do_scaffold(db, collection.id, collection.default_category_slug, auth.user.id)
    db.commit()
    db.refresh(collection)
    return CollectionRead.model_validate(collection)


@router.get("/{collection_id}", response_model=CollectionRead)
def get_collection(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_collection_role("viewer")),
) -> CollectionRead:
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    role = collection_role(db, auth.user, collection_id)
    return CollectionRead.model_validate(collection).model_copy(update={"my_role": role})


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
    auth: AuthContext = Depends(require_collection_role("owner")),
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
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="member.add",
        collection_id=collection_id,
        target_type="user",
        target_id=user.id,
        payload={"role": payload.role, "username": user.username},
    )
    db.commit()
    db.refresh(membership)
    return _membership_to_detail(membership, user)


@router.patch("/{collection_id}/members/{member_id}", response_model=MembershipDetail)
def update_member(
    collection_id: str,
    member_id: str,
    payload: MembershipUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_collection_role("owner")),
) -> MembershipDetail:
    membership = db.get(CollectionMembership, member_id)
    if membership is None or membership.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    old_role = membership.role
    membership.role = payload.role
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="member.update_role",
        collection_id=collection_id,
        target_type="user",
        target_id=membership.user_id,
        payload={"old_role": old_role, "new_role": payload.role},
    )
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
    auth: AuthContext = Depends(require_collection_role("owner")),
) -> None:
    membership = db.get(CollectionMembership, member_id)
    if membership is None or membership.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    audit.log(
        db,
        actor_user_id=auth.user.id,
        action="member.remove",
        collection_id=collection_id,
        target_type="user",
        target_id=membership.user_id,
        payload={"role": membership.role},
    )
    db.delete(membership)
    db.commit()


@router.get("/{collection_id}/reports/totals")
def get_collection_totals(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    """Get collection totals (item count, total value)."""
    if collection_role(db, auth.user, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    report = CollectionReport(db, collection)
    return report.generate_totals()


@router.get("/{collection_id}/reports/bom")
def get_collection_bom(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> StreamingResponse:
    """Download bill of materials as text file."""
    if collection_role(db, auth.user, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    report = CollectionReport(db, collection)
    bom_text = report.generate_bom_text()

    return StreamingResponse(
        iter([bom_text.encode("utf-8")]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=bom-{collection.name}.txt"},
    )


@router.get("/{collection_id}/reports/insurance-export")
def get_insurance_export(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> StreamingResponse:
    """Download insurance-friendly export (ZIP with CSV, photos, manifest)."""
    if collection_role(db, auth.user, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    report = CollectionReport(db, collection)
    zip_data = report.generate_insurance_export()

    return StreamingResponse(
        iter([zip_data]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=insurance-export-{collection.name}.zip"},
    )


@router.get("/{collection_id}/reports/disposed")
def get_disposed_items_report(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> dict:
    """Get report of disposed/sold/donated items with breakdown by type."""
    if collection_role(db, auth.user, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    report = CollectionReport(db, collection)
    return report.generate_disposed_items_report()


_ALLOWED_SUGGESTION_FIELDS = {"condition", "creator"}


@router.get("/{collection_id}/field-suggestions", response_model=list[str])
def get_field_suggestions(
    collection_id: str,
    field: str = Query(..., description="Field name: condition or creator"),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[str]:
    """Return distinct non-null values for a first-class item field across a collection.

    Used by the web UI to power type-ahead / datalist suggestions.
    """
    if field not in _ALLOWED_SUGGESTION_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"field must be one of: {', '.join(sorted(_ALLOWED_SUGGESTION_FIELDS))}",
        )
    if collection_role(db, auth.user, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    from tangible.models import Item  # local to avoid circular

    col = getattr(Item, field)
    rows = db.scalars(
        select(distinct(col))
        .where(Item.collection_id == collection_id)
        .where(col.is_not(None))
        .where(col != "")
        .order_by(col)
    ).all()
    return [str(r) for r in rows if r]

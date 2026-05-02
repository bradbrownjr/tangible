"""Contact endpoints (per-user)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, require_user
from tangible.db import get_session
from tangible.models import Contact
from tangible.schemas import ContactCreate, ContactRead, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactRead])
def list_contacts(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ContactRead]:
    stmt = select(Contact).where(Contact.owner_id == auth.user.id).order_by(Contact.name)
    return [ContactRead.model_validate(c) for c in db.scalars(stmt)]


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ContactRead:
    contact = Contact(owner_id=auth.user.id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return ContactRead.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: str,
    payload: ContactUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ContactRead:
    contact = db.get(Contact, contact_id)
    if contact is None or contact.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    db.commit()
    db.refresh(contact)
    return ContactRead.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    contact = db.get(Contact, contact_id)
    if contact is None or contact.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(contact)
    db.commit()

"""Loan endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import AuthContext, collection_role, require_user
from tangible.db import get_session
from tangible.models import Item, Loan
from tangible.schemas import LoanCreate, LoanRead, LoanUpdate

router = APIRouter(prefix="/loans", tags=["loans"])


def _check_item_access(
    db: DBSession, auth: AuthContext, item_id: str, *, write: bool
) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    role = collection_role(db, auth.user, item.collection_id)
    allowed = {"editor", "owner"} if write else {"viewer", "editor", "owner"}
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return item


@router.get("", response_model=list[LoanRead])
def list_loans(
    item_id: str | None = Query(default=None),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[LoanRead]:
    if item_id:
        _check_item_access(db, auth, item_id, write=False)
        stmt = select(Loan).where(Loan.item_id == item_id).order_by(Loan.loaned_at.desc())
    else:
        # Active loans across user's accessible items.
        stmt = (
            select(Loan)
            .join(Item, Loan.item_id == Item.id)
            .where(Loan.returned_at.is_(None))
            .order_by(Loan.loaned_at.desc())
        )
        loans = []
        for loan in db.scalars(stmt):
            role = collection_role(db, auth.user, loan.item.collection_id)
            if role:
                loans.append(LoanRead.model_validate(loan))
        return loans
    return [LoanRead.model_validate(loan) for loan in db.scalars(stmt)]


@router.post("", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def create_loan(
    payload: LoanCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> LoanRead:
    _check_item_access(db, auth, payload.item_id, write=True)
    loan = Loan(**payload.model_dump())
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return LoanRead.model_validate(loan)


@router.patch("/{loan_id}", response_model=LoanRead)
def update_loan(
    loan_id: str,
    payload: LoanUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> LoanRead:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _check_item_access(db, auth, loan.item_id, write=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, key, value)
    db.commit()
    db.refresh(loan)
    return LoanRead.model_validate(loan)


@router.delete("/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(
    loan_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _check_item_access(db, auth, loan.item_id, write=True)
    db.delete(loan)
    db.commit()

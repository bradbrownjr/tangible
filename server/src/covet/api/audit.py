"""Audit log query endpoint.

Admins can read the full log; collection owners can read entries scoped
to their collection by passing ``collection_id``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, collection_role, require_user
from covet.db import get_session
from covet.models import AuditLogEntry
from covet.schemas import AuditLogRead

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=list[AuditLogRead])
def list_audit_log(
    collection_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[AuditLogEntry]:
    if collection_id is None:
        if not auth.user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin only"
            )
        stmt = select(AuditLogEntry)
    else:
        # Owner-only for per-collection view; admins also allowed.
        if not auth.user.is_admin:
            role = collection_role(db, auth.user, collection_id)
            if role != "owner":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Owner access required",
                )
        stmt = select(AuditLogEntry).where(
            AuditLogEntry.collection_id == collection_id
        )

    rows = db.scalars(stmt.order_by(AuditLogEntry.created_at.desc()).limit(limit)).all()
    return list(rows)

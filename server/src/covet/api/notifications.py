"""Notification preference endpoints and alert digest send."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import AuthContext, require_user
from covet.config import Settings, get_settings
from covet.db import get_session
from covet.email import send_alert_digest
from covet.models.notification import NOTIFICATION_KINDS, NotificationPreference

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas (inline -- small enough not to warrant a separate file)
# ---------------------------------------------------------------------------


class NotificationPrefRead(BaseModel):
    kind: str
    email_enabled: bool
    push_enabled: bool
    browser_enabled: bool
    lead_days: int

    model_config = {"from_attributes": True}


class NotificationPrefUpdate(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True
    browser_enabled: bool = True
    lead_days: int = Field(default=7, ge=1, le=365)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[NotificationPrefRead])
def list_preferences(
    auth: AuthContext = Depends(require_user),
    db: DBSession = Depends(get_session),
) -> list[NotificationPreference]:
    """Return all notification preferences for the current user.

    Kinds that have no row are returned with defaults (enabled=True, lead_days=7).
    """
    rows = db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == auth.user.id
        )
    ).scalars().all()
    by_kind = {r.kind: r for r in rows}
    result: list[NotificationPreference] = []
    for kind in NOTIFICATION_KINDS:
        if kind in by_kind:
            result.append(by_kind[kind])
        else:
            # Return a virtual row with defaults (not persisted yet)
            pref = NotificationPreference()
            pref.kind = kind
            pref.email_enabled = True
            pref.push_enabled = True
            pref.browser_enabled = True
            pref.lead_days = 7
            result.append(pref)
    return result


@router.put("/{kind}", response_model=NotificationPrefRead)
def upsert_preference(
    kind: str,
    payload: NotificationPrefUpdate,
    auth: AuthContext = Depends(require_user),
    db: DBSession = Depends(get_session),
) -> NotificationPreference:
    """Create or update a notification preference for one alert kind."""
    if kind not in NOTIFICATION_KINDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown kind '{kind}'. Valid kinds: {', '.join(NOTIFICATION_KINDS)}",
        )
    pref = db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == auth.user.id,
            NotificationPreference.kind == kind,
        )
    ).scalar_one_or_none()
    if pref is None:
        pref = NotificationPreference(user_id=auth.user.id, kind=kind)
        db.add(pref)
    pref.email_enabled = payload.email_enabled
    pref.push_enabled = payload.push_enabled
    pref.browser_enabled = payload.browser_enabled
    pref.lead_days = payload.lead_days
    db.commit()
    db.refresh(pref)
    return pref


@router.post("/send-digest", status_code=status.HTTP_202_ACCEPTED)
def send_digest(
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_user),
    db: DBSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Trigger an immediate alert-digest email for the current user.

    Uses the user's enabled preferences + maximum lead_days to compute
    which alerts to include. Returns 202 immediately; email is sent in the
    background.
    """
    if not auth.user.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No email address on your account. Add one in your profile to receive notifications.",
        )

    prefs = db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == auth.user.id,
            NotificationPreference.email_enabled.is_(True),
        )
    ).scalars().all()

    if not prefs:
        return {"queued": False, "reason": "no_enabled_prefs"}

    within_days = max(p.lead_days for p in prefs)
    enabled_kinds = {p.kind for p in prefs}

    # Fetch alerts inline (import here to avoid circular import)
    from covet.api.inventory import _build_alerts

    all_alerts = _build_alerts(auth=auth, db=db, within_days=within_days)
    filtered = [
        {"kind": a.kind, "title": a.title, "due_at": a.due_at.isoformat() if a.due_at else None, "details": a.details}
        for a in all_alerts
        if a.kind in enabled_kinds
    ]

    if not filtered:
        return {"queued": False, "reason": "no_alerts"}

    username = auth.user.display_name or auth.user.user_identifier
    background_tasks.add_task(
        send_alert_digest,
        settings=settings,
        to_email=auth.user.email,
        username=username,
        alerts=filtered,
    )
    return {"queued": True, "count": len(filtered)}

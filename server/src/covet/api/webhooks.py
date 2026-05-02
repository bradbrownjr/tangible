"""Webhook management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from covet.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from covet.db import get_session
from covet.models import Webhook, WebhookDelivery
from covet.schemas import WebhookCreate, WebhookDeliveryRead, WebhookRead, WebhookUpdate

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/collections/{collection_id}", response_model=list[WebhookRead])
def list_webhooks(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[WebhookRead]:
    """List webhooks for a collection."""
    if collection_role(db, auth.user, collection_id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    webhooks = db.scalars(
        select(Webhook)
        .where(Webhook.collection_id == collection_id)
        .order_by(Webhook.created_at.desc())
    ).all()

    return [WebhookRead.model_validate(w) for w in webhooks]


@router.post("/collections/{collection_id}", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
def create_webhook(
    collection_id: str,
    payload: WebhookCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> WebhookRead:
    """Create a new webhook for a collection."""
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in ("editor", "owner"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    webhook = Webhook(
        collection_id=collection_id,
        owner_id=auth.user.id,
        url=str(payload.url),
        secret=payload.secret,
        active=payload.active,
        events=",".join(payload.events),
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return WebhookRead.model_validate(webhook)


@router.get("/{webhook_id}", response_model=WebhookRead)
def get_webhook(
    webhook_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> WebhookRead:
    """Get a specific webhook."""
    webhook = db.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if webhook.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return WebhookRead.model_validate(webhook)


@router.patch("/{webhook_id}", response_model=WebhookRead)
def update_webhook(
    webhook_id: str,
    payload: WebhookUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> WebhookRead:
    """Update a webhook."""
    webhook = db.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if webhook.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if payload.url is not None:
        webhook.url = str(payload.url)
    if payload.secret is not None:
        webhook.secret = payload.secret
    if payload.active is not None:
        webhook.active = payload.active
    if payload.events is not None:
        webhook.events = ",".join(payload.events)

    db.commit()
    db.refresh(webhook)
    return WebhookRead.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    """Delete a webhook."""
    webhook = db.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if webhook.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.delete(webhook)
    db.commit()


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryRead])
def list_webhook_deliveries(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[WebhookDeliveryRead]:
    """List delivery attempts for a webhook."""
    webhook = db.get(Webhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if webhook.owner_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    deliveries = db.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return [WebhookDeliveryRead.model_validate(d) for d in deliveries]

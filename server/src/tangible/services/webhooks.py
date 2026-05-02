"""Webhook service for managing and dispatching webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from structlog import get_logger

from tangible.models import Webhook, WebhookDelivery

logger = get_logger(__name__)


async def fire_webhook_event(
    db: DBSession,
    collection_id: str,
    event_type: str,
    payload: dict,
) -> None:
    """
    Fire a webhook event by delivering it to all active webhooks.

    Args:
        db: Database session
        collection_id: Collection ID where event occurred
        event_type: Type of event (e.g., "item.created")
        payload: Event payload to send
    """
    # Get all active webhooks for this collection that are subscribed to this event
    webhooks = db.scalars(
        select(Webhook).where(
            Webhook.collection_id == collection_id,
            Webhook.active.is_(True),
        )
    ).all()

    for webhook in webhooks:
        # Check if this webhook is subscribed to this event
        subscribed_events = webhook.events.split(",")
        if event_type not in subscribed_events:
            continue

        # Queue the delivery
        await _queue_webhook_delivery(db, webhook, event_type, payload)


async def _queue_webhook_delivery(
    db: DBSession,
    webhook: Webhook,
    event_type: str,
    payload: dict,
) -> None:
    """Queue a webhook delivery attempt."""
    payload_json = json.dumps(payload)

    # Create delivery log entry
    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload_json,
        attempt_number=1,
    )
    db.add(delivery)
    db.commit()

    # Attempt delivery
    await _deliver_webhook(db, webhook, delivery, payload_json)


async def _deliver_webhook(
    db: DBSession,
    webhook: Webhook,
    delivery: WebhookDelivery,
    payload_json: str,
) -> None:
    """Attempt to deliver a webhook."""
    try:
        headers = {"Content-Type": "application/json"}

        # Add HMAC signature if secret is configured
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(),
                payload_json.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Tangible-Signature"] = f"sha256={signature}"

        # Add event type header
        headers["X-Tangible-Event"] = delivery.event_type

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(str(webhook.url), content=payload_json, headers=headers)

            delivery.status_code = response.status_code
            if response.status_code in (200, 201, 202, 204):
                delivery.success = True
                logger.info(
                    "webhook_delivered",
                    webhook_id=webhook.id,
                    event_type=delivery.event_type,
                    status_code=response.status_code,
                )
            else:
                delivery.success = False
                delivery.error_message = f"HTTP {response.status_code}"
                logger.warning(
                    "webhook_delivery_failed",
                    webhook_id=webhook.id,
                    event_type=delivery.event_type,
                    status_code=response.status_code,
                )

    except httpx.TimeoutException:
        delivery.success = False
        delivery.error_message = "Request timeout"
        logger.warning(
            "webhook_delivery_timeout",
            webhook_id=webhook.id,
            event_type=delivery.event_type,
        )

    except Exception as e:
        delivery.success = False
        delivery.error_message = str(e)
        logger.warning(
            "webhook_delivery_error",
            webhook_id=webhook.id,
            event_type=delivery.event_type,
            error=str(e),
        )

    # Schedule retry if delivery failed
    if not delivery.success and delivery.attempt_number < webhook.retry_count:
        retry_at = datetime.now(UTC) + timedelta(seconds=webhook.retry_delay_seconds)
        delivery.next_retry_at = retry_at.isoformat()

    db.commit()


async def retry_failed_webhooks(db: DBSession) -> None:
    """Retry failed webhook deliveries that are due for retry."""
    now = datetime.now(UTC).isoformat()

    # Find deliveries that need retry
    pending = db.scalars(
        select(WebhookDelivery).where(
            WebhookDelivery.success.is_(False),
            WebhookDelivery.next_retry_at.isnot(None),
            WebhookDelivery.next_retry_at <= now,
        )
    ).all()

    for delivery in pending:
        webhook = db.get(Webhook, delivery.webhook_id)
        if webhook is None or not webhook.active:
            continue

        delivery.attempt_number += 1
        payload_json = delivery.payload

        await _deliver_webhook(db, webhook, delivery, payload_json)

"""Home Assistant integration endpoints.

Exposes read-only sensor data and a downloadable automation blueprint so
users can wire Tangible into their HA dashboards and automations without
writing custom REST sensor YAML by hand.

Auth: API token (Bearer) or session cookie — same as the rest of the API.
Rate: follows global limit.
"""

from __future__ import annotations

import textwrap
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.api.inventory import _build_alerts
from tangible.auth.deps import AuthContext, require_user
from tangible.db import get_session
from tangible.models import Collection, Item
from tangible.models.user import CollectionMembership

router = APIRouter(prefix="/ha", tags=["home-assistant"])


# ---------------------------------------------------------------------------
# Sensor payload shapes
# ---------------------------------------------------------------------------


class SensorState(BaseModel):
    """One Home Assistant sensor entity."""

    entity_id: str
    state: str
    attributes: dict


class HaSensorsResponse(BaseModel):
    generated_at: datetime
    sensors: list[SensorState]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug(text: str) -> str:
    """Convert a human label to a safe HA entity-id fragment."""
    return text.lower().replace(" ", "_").replace("-", "_").replace("'", "")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/sensors", response_model=HaSensorsResponse)
def ha_sensors(
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> HaSensorsResponse:
    """Return all readable collections as HA sensor entities.

    Each collection yields:
    - ``sensor.tangible_<slug>_item_count`` — total active item count
    - ``sensor.tangible_<slug>_low_stock_count`` — items below minimum_quantity
    - ``sensor.tangible_<slug>_overdue_alerts`` — alerts past due date
    - ``sensor.tangible_<slug>_due_soon_alerts`` — alerts within 7 days

    Integrate using HA's REST sensor platform:

    ```yaml
    sensor:
      - platform: rest
        resource: https://your-tangible-server/api/ha/sensors
        headers:
          Authorization: "Bearer YOUR_TOKEN"
        value_template: "{{ value_json.sensors | length }}"
        json_attributes:
          - sensors
        scan_interval: 900
    ```
    """
    # Collect all collections the user can read.
    memberships = db.execute(
        select(CollectionMembership).where(
            CollectionMembership.user_id == auth.user.id,
        )
    ).scalars().all()
    readable_ids = {m.collection_id for m in memberships}

    # Also include collections the user owns directly.
    owned = db.execute(
        select(Collection).where(Collection.owner_id == auth.user.id)
    ).scalars().all()
    for c in owned:
        readable_ids.add(c.id)

    sensors: list[SensorState] = []

    for cid in readable_ids:
        collection = db.get(Collection, cid)
        if collection is None:
            continue

        slug = _slug(collection.name)
        prefix = f"sensor.tangible_{slug}"

        # Item count
        active_items = db.execute(
            select(Item).where(
                Item.collection_id == cid,
                Item.archived_at.is_(None),
            )
        ).scalars().all()
        item_count = len(active_items)

        # Low stock
        low_stock = sum(
            1 for it in active_items
            if it.minimum_quantity is not None and it.quantity <= it.minimum_quantity
        )

        # Alerts
        all_alerts = _build_alerts(db=db, auth=auth, within_days=7, collection_id=cid)
        now = datetime.now(UTC)
        overdue = [a for a in all_alerts if a.due_at and a.due_at < now]
        due_soon = [a for a in all_alerts if a.due_at and a.due_at >= now]

        sensors.extend([
            SensorState(
                entity_id=f"{prefix}_item_count",
                state=str(item_count),
                attributes={
                    "collection_id": cid,
                    "collection_name": collection.name,
                    "unit_of_measurement": "items",
                    "icon": "mdi:package-variant",
                },
            ),
            SensorState(
                entity_id=f"{prefix}_low_stock_count",
                state=str(low_stock),
                attributes={
                    "collection_id": cid,
                    "collection_name": collection.name,
                    "unit_of_measurement": "items",
                    "icon": "mdi:package-variant-minus",
                    "items": [
                        {"id": it.id, "title": it.title, "quantity": it.quantity, "minimum": it.minimum_quantity}
                        for it in active_items
                        if it.minimum_quantity is not None and it.quantity <= it.minimum_quantity
                    ],
                },
            ),
            SensorState(
                entity_id=f"{prefix}_overdue_alerts",
                state=str(len(overdue)),
                attributes={
                    "collection_id": cid,
                    "collection_name": collection.name,
                    "unit_of_measurement": "alerts",
                    "icon": "mdi:alert-circle",
                    "alerts": [
                        {"id": a.id, "kind": a.kind, "title": a.title, "due_at": a.due_at.isoformat() if a.due_at else None}
                        for a in overdue[:10]
                    ],
                },
            ),
            SensorState(
                entity_id=f"{prefix}_due_soon_alerts",
                state=str(len(due_soon)),
                attributes={
                    "collection_id": cid,
                    "collection_name": collection.name,
                    "unit_of_measurement": "alerts",
                    "icon": "mdi:calendar-clock",
                    "alerts": [
                        {"id": a.id, "kind": a.kind, "title": a.title, "due_at": a.due_at.isoformat() if a.due_at else None}
                        for a in due_soon[:10]
                    ],
                },
            ),
        ])

    return HaSensorsResponse(generated_at=datetime.now(UTC), sensors=sensors)


@router.get("/blueprint.yaml", response_class=PlainTextResponse)
def ha_blueprint(
    auth: AuthContext = Depends(require_user),
) -> str:
    """Download a Home Assistant automation blueprint for Tangible alerts.

    Import into HA via Settings > Automations > Blueprints > Import Blueprint,
    then paste this URL (or self-hosted equivalent) into the import dialog.
    """
    return textwrap.dedent("""
        blueprint:
          name: Tangible — Alert Notification
          description: >
            Sends a persistent notification when a Tangible collection has overdue
            or due-soon alerts. Requires a REST sensor named
            `sensor.tangible_<collection>_overdue_alerts` configured to poll your
            Tangible server.
          domain: automation
          input:
            overdue_sensor:
              name: Overdue alerts sensor
              description: >
                The `sensor.tangible_*_overdue_alerts` entity for your collection.
              selector:
                entity:
                  integration: rest
            due_soon_sensor:
              name: Due soon alerts sensor
              description: >
                The `sensor.tangible_*_due_soon_alerts` entity for your collection.
              selector:
                entity:
                  integration: rest
            notify_target:
              name: Notification target
              description: Service to call (e.g. `notify.mobile_app_my_phone`).
              selector:
                text: {}

        trigger:
          - platform: state
            entity_id: !input overdue_sensor
          - platform: state
            entity_id: !input due_soon_sensor

        condition:
          - condition: or
            conditions:
              - condition: numeric_state
                entity_id: !input overdue_sensor
                above: 0
              - condition: numeric_state
                entity_id: !input due_soon_sensor
                above: 0

        action:
          - service: !input notify_target
            data:
              title: "Tangible — Attention needed"
              message: >
                {% set overdue = states(overdue_sensor) | int(0) %}
                {% set soon = states(due_soon_sensor) | int(0) %}
                {{ overdue }} overdue, {{ soon }} due within 7 days.
    """).lstrip()

"""Model Context Protocol (MCP) server for Covet.

Exposes a read-only set of MCP tools so AI assistants (Claude, Copilot,
GPT, etc.) can query your inventory, maintenance history, and stock levels
in natural language.

Mount:
    The FastAPI app mounts this at ``/mcp`` via ``app.mount("/mcp", mcp_app())``.

Auth:
    All tool calls require a Bearer API token in the ``Authorization`` header,
    identical to the rest of the Covet API.  Configure your AI client with:
        URL:   https://<your-host>/mcp
        Token: <api token from Settings → API Tokens>

Tools exposed:
    - list_collections     — enumerate all readable collections
    - search_items         — full-text / filter search across items
    - get_item             — fetch one item by ID
    - list_maintenance     — list maintenance tasks for an item
    - list_due_alerts      — upcoming/overdue alerts across all collections
    - list_low_stock       — items below their minimum quantity
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DBSession
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from covet.auth.deps import AuthContext, collection_role
from covet.auth.service import api_token_user, session_for_token
from covet.config import Settings
from covet.db import get_engine
from covet.models import (
    Collection,
    CollectionMembership,
    Item,
    MaintenanceCompletion,
    MaintenanceTask,
)

# ---------------------------------------------------------------------------
# Session helper (MCP tools run outside FastAPI's dependency injection)
# ---------------------------------------------------------------------------


def _new_session() -> DBSession:
    """Open a new SQLAlchemy session using the initialized engine."""
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)()

# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

_UNAUTHENTICATED = JSONResponse(
    {"error": "Unauthorized — provide a Bearer API token or session cookie"},
    status_code=401,
)
_FORBIDDEN = JSONResponse({"error": "Forbidden"}, status_code=403)


class _BearerAuthMiddleware(BaseHTTPMiddleware):
    """Validate Bearer token or session cookie before any MCP call."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Allow unauthenticated probing of the SSE/HTTP endpoint metadata.
        if request.method in {"GET", "HEAD"} and request.url.path.endswith("/"):
            return await call_next(request)

        settings: Settings = request.app.state.covet_settings
        db: DBSession = _new_session()
        try:
            auth_header = request.headers.get("authorization", "")
            raw_token: str | None = None
            if auth_header.lower().startswith("bearer "):
                raw_token = auth_header.split(" ", 1)[1].strip() or None

            user = None
            if raw_token:
                user = api_token_user(db, raw_token=raw_token)
            else:
                cookie = request.cookies.get(settings.session_cookie_name)
                if cookie:
                    sess = session_for_token(db, raw_token=cookie)
                    if sess is not None:
                        from covet.models import User
                        user = db.get(User, sess.user_id)

            if user is None or not user.is_active:
                return _UNAUTHENTICATED

            # Stash on request state so tools can retrieve it.
            request.state.covet_user_id = user.id
        finally:
            db.close()

        return await call_next(request)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _readable_collection_ids(db: DBSession, user_id: str) -> list[str]:
    """Return IDs of all collections the user can read."""
    owned = db.scalars(select(Collection.id).where(Collection.owner_id == user_id)).all()
    membered = db.scalars(
        select(CollectionMembership.collection_id)
        .where(CollectionMembership.user_id == user_id)
        .distinct()
    ).all()
    all_ids = list({*owned, *membered})

    # Filter to actual viewer-or-better role (respects soft rules)
    from covet.models import User
    user_obj = db.get(User, user_id)
    if user_obj is None:
        return []
    readable = []
    for cid in all_ids:
        role = collection_role(db, user_obj, cid)
        if role in {"viewer", "editor", "owner"}:
            readable.append(cid)
    return readable


def _item_to_dict(item: Item, db: DBSession | None = None) -> dict[str, Any]:
    location_path: str | None = None
    if item.location_id and db is not None:
        from covet.models import Location
        loc = db.get(Location, item.location_id)
        if loc is not None:
            location_path = loc.full_path if hasattr(loc, "full_path") else loc.name
    return {
        "id": item.id,
        "title": item.title,
        "subtitle": item.subtitle,
        "notes": item.notes,
        "condition": item.condition,
        "quantity": item.quantity,
        "minimum_quantity": item.minimum_quantity,
        "depleted": item.depleted,
        "wanted": item.wanted,
        "purchase_price": float(item.purchase_price) if item.purchase_price else None,
        "current_value": float(item.current_value) if item.current_value else None,
        "currency": item.currency,
        "acquired_at": item.acquired_at.isoformat() if item.acquired_at else None,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "use_by_date": item.use_by_date.isoformat() if item.use_by_date else None,
        "location": location_path,
        "collection_id": item.collection_id,
        "attrs": item.attrs,
        "identifiers": item.identifiers,
    }


def _task_to_dict(task: MaintenanceTask, last_completion: MaintenanceCompletion | None) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "interval_days": task.interval_days,
        "next_due_at": task.next_due_at.isoformat() if task.next_due_at else None,
        "last_completed_at": task.last_completed_at.isoformat() if task.last_completed_at else None,
        "last_completion_note": last_completion.notes if last_completion else None,
        "overdue": (
            task.next_due_at is not None and task.next_due_at < datetime.now(UTC)
        ),
    }


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------

def build_mcp_server(settings: Settings) -> FastMCP:
    """Build and return a configured FastMCP instance."""

    mcp = FastMCP(
        "Covet",
        instructions=(
            "You have access to the user's Covet home inventory. "
            "Use these tools to answer questions about what they own, "
            "maintenance history, stock levels, and upcoming due dates."
        ),
    )

    # ------------------------------------------------------------------
    # Tool: list_collections
    # ------------------------------------------------------------------

    @mcp.tool(
        description="List all collections the user can access. Returns id, name, description."
    )
    def list_collections(user_id: str) -> list[dict]:
        """Return all readable collections for the given user."""
        db = _new_session()
        try:
            from sqlalchemy import func
            cids = _readable_collection_ids(db, user_id)
            rows = db.scalars(select(Collection).where(Collection.id.in_(cids))).all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "item_count": db.scalar(
                        select(func.count(Item.id)).where(
                            Item.collection_id == c.id, Item.archived_at.is_(None)
                        )
                    ) or 0,
                }
                for c in rows
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Tool: search_items
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Search items across the user's collections. "
            "Pass a query string for full-text search. "
            "Optionally filter by collection_id, include_archived, or depleted. "
            "Returns up to 50 results."
        )
    )
    def search_items(
        user_id: str,
        query: str = "",
        collection_id: str = "",
        include_archived: bool = False,
        depleted: bool | None = None,
        wanted: bool | None = None,
        limit: int = 50,
    ) -> list[dict]:
        db = _new_session()
        try:
            cids = _readable_collection_ids(db, user_id)
            if collection_id:
                if collection_id not in cids:
                    return []
                cids = [collection_id]
            if not cids:
                return []

            stmt = select(Item).where(Item.collection_id.in_(cids))
            if not include_archived:
                stmt = stmt.where(Item.archived_at.is_(None))
            if depleted is not None:
                stmt = stmt.where(Item.depleted.is_(depleted))
            if wanted is not None:
                stmt = stmt.where(Item.wanted.is_(wanted))
            if query:
                q = f"%{query}%"
                stmt = stmt.where(
                    or_(
                        Item.title.ilike(q),
                        Item.subtitle.ilike(q),
                        Item.notes.ilike(q),
                    )
                )
            stmt = stmt.order_by(Item.title).limit(min(limit, 100))
            items = db.scalars(stmt).all()
            return [_item_to_dict(i, db) for i in items]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Tool: get_item
    # ------------------------------------------------------------------

    @mcp.tool(
        description="Fetch full details of a single item by its ID."
    )
    def get_item(user_id: str, item_id: str) -> dict | None:
        db = _new_session()
        try:
            item = db.get(Item, item_id)
            if item is None:
                return None
            cids = _readable_collection_ids(db, user_id)
            if item.collection_id not in cids:
                return None
            return _item_to_dict(item, db)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Tool: list_maintenance
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "List maintenance tasks for an item. "
            "Includes interval, next due date, last completed date, and whether overdue."
        )
    )
    def list_maintenance(user_id: str, item_id: str) -> list[dict] | str:
        db = _new_session()
        try:
            item = db.get(Item, item_id)
            if item is None:
                return "Item not found."
            cids = _readable_collection_ids(db, user_id)
            if item.collection_id not in cids:
                return "Access denied."

            tasks = db.scalars(
                select(MaintenanceTask)
                .where(MaintenanceTask.item_id == item_id)
                .order_by(MaintenanceTask.next_due_at.is_(None), MaintenanceTask.next_due_at)
            ).all()

            result = []
            for task in tasks:
                last = db.scalar(
                    select(MaintenanceCompletion)
                    .where(MaintenanceCompletion.task_id == task.id)
                    .order_by(MaintenanceCompletion.completed_at.desc())
                )
                result.append(_task_to_dict(task, last))
            return result
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Tool: list_due_alerts
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Return upcoming and overdue alerts (maintenance, expiry, use-by, low-stock) "
            "across all the user's collections. "
            "within_days controls how far ahead to look (default 30)."
        )
    )
    def list_due_alerts(user_id: str, within_days: int = 30) -> list[dict]:
        db = _new_session()
        try:
            from covet.models import User
            user = db.get(User, user_id)
            if user is None:
                return []
            auth = AuthContext(user=user, via="token")
            from covet.api.inventory import _build_alerts
            alerts = _build_alerts(auth=auth, db=db, within_days=within_days)
            return [
                {
                    "id": a.id,
                    "kind": a.kind,
                    "severity": a.severity,
                    "title": a.title,
                    "due_at": a.due_at.isoformat() if a.due_at else None,
                    "collection_id": a.collection_id,
                    "item_id": a.item_id,
                    "details": a.details,
                }
                for a in alerts
            ]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Tool: list_low_stock
    # ------------------------------------------------------------------

    @mcp.tool(
        description=(
            "Return items whose quantity is at or below their minimum_quantity threshold. "
            "Useful for answering 'do I have enough X?' questions."
        )
    )
    def list_low_stock(user_id: str, collection_id: str = "") -> list[dict]:
        db = _new_session()
        try:
            cids = _readable_collection_ids(db, user_id)
            if collection_id:
                if collection_id not in cids:
                    return []
                cids = [collection_id]
            if not cids:
                return []

            stmt = (
                select(Item)
                .where(
                    Item.collection_id.in_(cids),
                    Item.minimum_quantity.isnot(None),
                    Item.quantity <= Item.minimum_quantity,
                    Item.archived_at.is_(None),
                )
                .order_by(Item.title)
            )
            return [_item_to_dict(i, db) for i in db.scalars(stmt).all()]
        finally:
            db.close()

    return mcp


def mcp_app(settings: Settings) -> Starlette:
    """Return a mounted Starlette app for the MCP server."""
    server = build_mcp_server(settings)
    app = server.streamable_http_app()
    # Stash settings so the auth middleware can reach them.
    app.state.covet_settings = settings
    # Wrap with auth middleware.
    app.add_middleware(_BearerAuthMiddleware)
    return app

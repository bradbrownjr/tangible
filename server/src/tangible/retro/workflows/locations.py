"""Locations workflow — browse locations and see what's stored there.

Commands:
  BROWSE  Browse locations for a collection
  0       Return to main menu

Within the location list:
  <n>     Select a location → see items stored there
  N/P     Next / previous page
  0       Back
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from tangible.retro.command_router import CommandExit
from tangible.retro.layout import Screen, clear_screen

if TYPE_CHECKING:
    from tangible.retro.session import TelnetSession

log = logging.getLogger(__name__)

PAGE_SIZE = 12


def _idle_check(exc: Exception) -> None:
    from tangible.retro.session import _IdleTimeout
    raise _IdleTimeout() from exc


async def _readline(session: "TelnetSession") -> str:
    try:
        return await session.transport.readline()
    except (TimeoutError, ConnectionResetError) as exc:
        _idle_check(exc)
    return ""  # unreachable


def _auth_filter(user, Collection):
    return (Collection.owner_id == user.id) | Collection.memberships.any(user_id=user.id)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def locations_menu(session: "TelnetSession") -> None:
    """Main locations submenu."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "LOCATIONS"
        screen.add_rows([
            "",
            "   BROWSE  Browse locations and their contents",
            "",
            "   0       Return to main menu",
            "",
        ])
        screen.set_hints("BROWSE=Locations  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd_input = (await _readline(session)).strip().upper()

        if not cmd_input or cmd_input in ("MENU", "BACK", "0"):
            raise CommandExit("menu")

        parts = cmd_input.split(maxsplit=1)
        command = parts[0]

        if command == "BROWSE":
            await _browse_locations(session)


# ---------------------------------------------------------------------------
# Location browse
# ---------------------------------------------------------------------------

async def _browse_locations(session: "TelnetSession") -> None:
    """Show a flat list of all locations across accessible collections."""
    from tangible.models.collection import Collection
    from tangible.models.location import Location
    from tangible.models.user import User

    engine = session.engine
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if user is None:
            return
        user_id = user.id

    page = 0

    while True:
        with Session() as db:
            u = db.get(User, user_id)
            locations = db.scalars(
                select(Location)
                .join(Collection, Location.collection_id == Collection.id)
                .where(_auth_filter(u, Collection))
                .order_by(Collection.name, Location.name)
            ).all()

        total = len(locations)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages - 1)
        start = page * PAGE_SIZE
        slice_ = locations[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = f"LOCATIONS  ({total} total)"

        if not slice_:
            screen.add_rows(["", "   No locations found.", ""])
        else:
            screen.add_rows([""])
            for i, loc in enumerate(slice_, start=1):
                parent_str = f" > {loc.parent.name}" if loc.parent_id and loc.parent else ""
                coll_name = loc.collection.name[:18] if loc.collection else ""
                line = f"   {i:2}. {loc.name[:40]:<40}{parent_str[:18]:<18} [{coll_name}]"
                screen.add_rows([line])

        nav = []
        if page > 0:
            nav.append("P=Prev")
        if page < pages - 1:
            nav.append("N=Next")
        nav.append("0=Back")
        screen.set_hints("  ".join(nav))
        screen.set_prompt(f"SELECT (1-{len(slice_)}) or N/P/0 ===> ")

        await session.transport.write(clear_screen() + screen.render())
        raw = (await _readline(session)).strip().upper()

        if not raw or raw == "0":
            return
        if raw == "N" and page < pages - 1:
            page += 1
            continue
        if raw == "P" and page > 0:
            page -= 1
            continue

        try:
            idx = int(raw) - 1
        except ValueError:
            continue
        if 0 <= idx < len(slice_):
            await _location_contents(session, slice_[idx].id, user_id)


async def _location_contents(
    session: "TelnetSession", location_id: str, user_id: str
) -> None:
    """Show all items stored at a given location, paginated."""
    from tangible.models.collection import Collection
    from tangible.models.item import Item
    from tangible.models.location import Location
    from tangible.models.user import User

    engine = session.engine
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    page = 0

    while True:
        with Session() as db:
            loc = db.get(Location, location_id)
            if loc is None:
                return
            loc_name = loc.name
            coll_name = loc.collection.name if loc.collection else ""
            parent_name = loc.parent.name if loc.parent else None

            u = db.get(User, user_id)
            items = db.scalars(
                select(Item)
                .join(Collection, Item.collection_id == Collection.id)
                .where(
                    Item.location_id == location_id,
                    Item.archived_at.is_(None),
                    _auth_filter(u, Collection),
                )
                .order_by(Item.title)
            ).all()

        total = len(items)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages - 1)
        start = page * PAGE_SIZE
        slice_ = items[start : start + PAGE_SIZE]

        breadcrumb = f"{coll_name} / {parent_name} / {loc_name}" if parent_name else f"{coll_name} / {loc_name}"

        screen = Screen(operator=session.username or "")
        screen.title = f"LOCATION: {loc_name[:50]}"
        screen.add_rows([
            "",
            f"   {breadcrumb[:74]}",
            f"   {total} item{'s' if total != 1 else ''} stored here",
            "",
        ])

        if not slice_:
            screen.add_rows(["   (empty)", ""])
        else:
            for i, item in enumerate(slice_, start=1):
                qty_str = f"x{item.quantity}" if item.quantity and item.quantity != 1 else ""
                line = f"   {i:2}. {item.title[:64]:<64} {qty_str}"
                screen.add_rows([line])

        nav = []
        if page > 0:
            nav.append("P=Prev")
        if page < pages - 1:
            nav.append("N=Next")
        nav.append("0=Back")
        screen.set_hints("  ".join(nav))
        screen.set_prompt("N/P/0 ===> ")

        await session.transport.write(clear_screen() + screen.render())
        raw = (await _readline(session)).strip().upper()

        if not raw or raw == "0":
            return
        if raw == "N" and page < pages - 1:
            page += 1
        elif raw == "P" and page > 0:
            page -= 1

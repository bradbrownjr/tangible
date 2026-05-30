"""Inventory lookup and search workflow.

Commands:
  ITEM <id/barcode>  - Lookup item by ID or barcode (inline or prompted)
  FIND <keyword>     - Search items by title/keyword (inline or prompted)
  ADJ                - From item detail, adjust quantity/location/condition
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from tangible.retro.command_router import CommandExit
from tangible.retro.layout import Screen, clear_screen

if TYPE_CHECKING:
    from tangible.retro.session import TelnetSession

log = logging.getLogger(__name__)

PAGE_SIZE = 12


def _idle_check(exc: Exception) -> None:
    """Re-raise TimeoutError/ConnectionResetError as _IdleTimeout."""
    from tangible.retro.session import _IdleTimeout
    raise _IdleTimeout() from exc


async def _readline(session: "TelnetSession") -> str:
    """Read a line, converting transport errors to _IdleTimeout."""
    try:
        return await session.transport.readline()
    except (TimeoutError, ConnectionResetError) as exc:
        _idle_check(exc)
    return ""  # unreachable


async def inventory_menu(session: "TelnetSession") -> None:
    """Main inventory submenu: accepts inline or bare commands."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "INVENTORY"
        screen.add_rows([
            "",
            "   ITEM <id>     Lookup item by ID or barcode",
            "   FIND <text>   Search items by title / keyword",
            "",
            "   0             Return to main menu",
            "",
        ])
        screen.set_hints("ITEM=Lookup  FIND=Search  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd_input = (await _readline(session)).strip().upper()

        if not cmd_input or cmd_input in ("MENU", "BACK"):
            raise CommandExit("menu")
        if cmd_input == "0":
            raise CommandExit("menu")

        parts = cmd_input.split(maxsplit=1)
        command = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command == "ITEM":
            if not arg:
                await session.transport.write("   ITEM ID ===> ")
                arg = (await _readline(session)).strip()
            if arg:
                await _inventory_item(session, arg)
        elif command == "FIND":
            if not arg:
                await session.transport.write("   SEARCH ===> ")
                arg = (await _readline(session)).strip()
            if arg:
                await _inventory_find(session, arg)
        # Unrecognized: silently redraw menu


async def _get_user(session: "TelnetSession", db):
    """Fetch current user from DB. Returns None and writes error if missing."""
    from sqlalchemy import select
    from tangible.models.user import User
    user = db.scalar(select(User).where(User.username == session.username))
    if not user:
        await session.transport.writeln("\r\n   ERROR: USER SESSION INVALID.\r\n")
    return user


def _auth_filter(user, Collection):
    """SQLAlchemy WHERE clause: collections the user owns or is a member of."""
    return (Collection.owner_id == user.id) | Collection.memberships.any(user_id=user.id)


async def _inventory_item(session: "TelnetSession", lookup: str) -> None:
    """Lookup item by ID or barcode; show detail screen."""
    from tangible.models.collection import Collection
    from tangible.models.item import Item
    from tangible.models.loan import Loan

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    with Session() as db:
        user = await _get_user(session, db)
        if not user:
            return

        # Try ID match first, then barcode JSON field
        item = db.scalar(
            select(Item).join(Item.collection).where(
                Item.id == lookup,
                _auth_filter(user, Collection),
            )
        )
        if not item:
            item = db.scalar(
                select(Item).join(Item.collection).where(
                    Item.identifiers["barcode"].astext == lookup,
                    _auth_filter(user, Collection),
                )
            )

        if not item:
            screen = Screen(operator=session.username or "")
            screen.title = "ITEM LOOKUP"
            screen.set_message(f"NOT FOUND: {lookup[:40]}")
            screen.set_hints("0=Back")
            screen.set_prompt("COMMAND ===> ")
            await session.transport.write(clear_screen() + screen.render())
            await _readline(session)
            return

        item_id = item.id

    # Show detail (pass ID so each redraw fetches fresh data)
    await _show_item_detail(session, item_id)


async def _inventory_find(session: "TelnetSession", search_term: str) -> None:
    """Search items by title; show paginated results."""
    from tangible.models.collection import Collection
    from tangible.models.item import Item

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    with Session() as db:
        user = await _get_user(session, db)
        if not user:
            return

        like = f"%{search_term}%"
        rows = db.execute(
            select(Item.id, Item.title, Item.quantity, Item.location_id)
            .join(Item.collection)
            .where(Item.title.ilike(like), _auth_filter(user, Collection))
            .order_by(Item.title)
        ).all()

    if not rows:
        screen = Screen(operator=session.username or "")
        screen.title = "SEARCH RESULTS"
        screen.set_message(f"NO ITEMS FOUND: {search_term[:40]}")
        screen.set_hints("0=Back")
        screen.set_prompt("COMMAND ===> ")
        await session.transport.write(clear_screen() + screen.render())
        await _readline(session)
        return

    total = len(rows)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = 0

    while True:
        start = page * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = f"SEARCH: {search_term[:30]}  ({total} FOUND)"
        screen.add_rows([
            "",
            f"   Page {page + 1} of {total_pages}",
            "",
            f"   {'#':<4} {'TITLE':<44} {'QTY':>3}  LOCATION",
            "   " + "-" * 72,
        ])
        for i, row in enumerate(page_rows, 1):
            title = (row.title or "")[:43].ljust(43)
            qty = str(row.quantity or 0).rjust(3)
            loc = (row.location_id or "")[:14].ljust(14)
            screen.add_row(f"   {i:<4} {title}  {qty}  {loc}")
        screen.add_row("   " + "-" * 72)

        # Build navigation hints
        nav = []
        if page > 0:
            nav.append("P=PREV")
        if page < total_pages - 1:
            nav.append("N=NEXT")
        nav.append("0=BACK")
        screen.set_hints("  ".join(nav))
        screen.set_prompt("SELECT # ===> ")

        await session.transport.write(clear_screen() + screen.render())
        choice = (await _readline(session)).strip().upper()

        if choice == "0" or choice in ("MENU", "BACK"):
            return
        elif choice == "N" and page < total_pages - 1:
            page += 1
        elif choice == "P" and page > 0:
            page -= 1
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(page_rows):
                await _show_item_detail(session, page_rows[idx].id)
            # Else: invalid number, redraw


async def _show_item_detail(session: "TelnetSession", item_id: str) -> None:
    """Display full item detail. Reloads fresh from DB on each loop iteration."""
    from tangible.models.collection import Collection
    from tangible.models.contact import Contact
    from tangible.models.item import Item
    from tangible.models.loan import Loan

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    while True:
        with Session() as db:
            item = db.scalar(select(Item).where(Item.id == item_id))
            if not item:
                return

            coll = db.scalar(select(Collection).where(Collection.id == item.collection_id))
            loan = db.scalar(
                select(Loan).where(
                    Loan.item_id == item_id,
                    Loan.returned_at.is_(None),
                )
            )
            borrower_name = None
            if loan and loan.contact_id:
                contact = db.scalar(select(Contact).where(Contact.id == loan.contact_id))
                borrower_name = contact.name if contact else loan.contact_id

            # Snapshot values while session open
            title = item.title or ""
            item_id_str = item.id
            coll_name = coll.name if coll else "unknown"
            quantity = item.quantity
            location = item.location_id or "(not set)"
            condition = item.condition or "unknown"
            acquired = str(item.acquired_at.date()) if item.acquired_at else "unknown"
            loan_line = (
                f"YES — Due {loan.due_at.date() if loan.due_at else 'N/A'}  "
                f"Borrower: {borrower_name or 'unknown'}"
                if loan else "NO"
            )

        screen = Screen(operator=session.username or "")
        screen.title = "ITEM DETAIL"
        screen.add_rows([
            "",
            f"   {'TITLE':<14} {title[:60]}",
            f"   {'ID':<14} {item_id_str}",
            f"   {'COLLECTION':<14} {coll_name}",
            f"   {'QUANTITY':<14} {quantity}",
            f"   {'LOCATION':<14} {location}",
            f"   {'CONDITION':<14} {condition}",
            f"   {'ACQUIRED':<14} {acquired}",
            f"   {'ON LOAN':<14} {loan_line}",
            "",
            "   " + "-" * 60,
            "   ADJ    Adjust quantity / location / condition",
            "   0      Back",
        ])
        screen.set_hints("ADJ=Adjust  0=Back")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd = (await _readline(session)).strip().upper()

        if cmd == "0" or cmd in ("BACK", "MENU"):
            return
        elif cmd == "ADJ":
            await _adjust_item(session, item_id)
            # Loop back — next iteration reloads fresh item data
        # Else: unrecognized, redraw


async def _adjust_item(session: "TelnetSession", item_id: str) -> None:
    """Adjust quantity, location, or condition for an item."""
    from tangible.models.item import Item

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "ADJUST ITEM"
        screen.add_rows([
            "",
            "   1   Quantity",
            "   2   Location",
            "   3   Condition",
            "",
            "   0   Back",
            "",
        ])
        screen.set_hints("1=Qty  2=Loc  3=Cond  0=Back")
        screen.set_prompt("SELECTION ===> ")

        await session.transport.write(clear_screen() + screen.render())
        choice = (await _readline(session)).strip().upper()

        if choice == "0":
            return

        if choice == "1":
            await session.transport.write("\r\n   NEW QUANTITY ===> ")
            val = (await _readline(session)).strip()
            if val.isdigit():
                with Session() as db:
                    db.execute(update(Item).where(Item.id == item_id).values(quantity=int(val)))
                    db.commit()
                screen = Screen(operator=session.username or "")
                screen.set_message(f"QUANTITY UPDATED TO {val}.")
                screen.set_hints("0=Back  ADJ=More Adjustments")
                screen.set_prompt("COMMAND ===> ")
                await session.transport.write(clear_screen() + screen.render())
                await _readline(session)
                return
            else:
                screen = Screen(operator=session.username or "")
                screen.set_message("INVALID — ENTER A WHOLE NUMBER.")
                await session.transport.write(clear_screen() + screen.render())
                await _readline(session)

        elif choice == "2":
            await session.transport.write("\r\n   NEW LOCATION ===> ")
            val = (await _readline(session)).strip()
            if val:
                with Session() as db:
                    db.execute(update(Item).where(Item.id == item_id).values(location_id=val))
                    db.commit()
                screen = Screen(operator=session.username or "")
                screen.set_message(f"LOCATION UPDATED TO: {val[:50]}")
                screen.set_prompt("COMMAND ===> ")
                await session.transport.write(clear_screen() + screen.render())
                await _readline(session)
                return

        elif choice == "3":
            await session.transport.write("\r\n   NEW CONDITION ===> ")
            val = (await _readline(session)).strip()
            if val:
                with Session() as db:
                    db.execute(update(Item).where(Item.id == item_id).values(condition=val))
                    db.commit()
                screen = Screen(operator=session.username or "")
                screen.set_message(f"CONDITION UPDATED TO: {val[:50]}")
                screen.set_prompt("COMMAND ===> ")
                await session.transport.write(clear_screen() + screen.render())
                await _readline(session)
                return

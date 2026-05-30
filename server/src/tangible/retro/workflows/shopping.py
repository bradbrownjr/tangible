"""Shopping workflow — browse and mark items purchased.

Commands:
  LIST    Browse the active shopping list for a collection
  0       Return to main menu

Within the list:
  <n>     Select an item → detail screen
  N/P     Next / previous page
  0       Back to menu

Within an item detail:
  BUY     Mark purchased (stamps purchased_at + purchased_by)
  0       Back to list
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
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

async def shopping_menu(session: "TelnetSession") -> None:
    """Main shopping submenu."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "SHOPPING"
        screen.add_rows([
            "",
            "   LIST    Browse active shopping list",
            "",
            "   0       Return to main menu",
            "",
        ])
        screen.set_hints("LIST=Browse  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd_input = (await _readline(session)).strip().upper()

        if not cmd_input or cmd_input in ("MENU", "BACK", "0"):
            raise CommandExit("menu")

        parts = cmd_input.split(maxsplit=1)
        command = parts[0]

        if command == "LIST":
            await _shopping_list(session)


# ---------------------------------------------------------------------------
# List browsing
# ---------------------------------------------------------------------------

async def _shopping_list(session: "TelnetSession") -> None:
    """Browse unpurchased shopping items across all accessible collections."""
    from tangible.models.collection import Collection
    from tangible.models.shopping import ShoppingItem
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
            rows = db.scalars(
                select(ShoppingItem)
                .join(Collection, ShoppingItem.collection_id == Collection.id)
                .where(
                    _auth_filter(u, Collection),
                    ShoppingItem.purchased_at.is_(None),
                )
                .order_by(ShoppingItem.list_type, ShoppingItem.name)
            ).all()

        total = len(rows)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages - 1)
        start = page * PAGE_SIZE
        slice_ = rows[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = f"SHOPPING LIST  ({total} items)"

        if not slice_:
            screen.add_rows(["", "   Nothing on the list.", ""])
        else:
            screen.add_rows([""])
            for i, item in enumerate(slice_, start=1):
                qty_str = f"{item.quantity}" if item.quantity and item.quantity != 1 else ""
                unit_str = f" {item.unit}" if item.unit else ""
                name_part = f"{item.name}"
                right = f"{qty_str}{unit_str}".strip()
                coll = item.collection.name[:20] if item.collection else ""
                line = f"   {i:2}. {name_part[:44]:<44} {right:>6}  {coll}"
                screen.add_rows([line])

        nav = []
        if page > 0:
            nav.append("P=Prev")
        if page < pages - 1:
            nav.append("N=Next")
        nav.append("0=Menu")
        screen.set_hints("  ".join(nav) if nav else "0=Menu")
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
            item_id = slice_[idx].id
            await _shopping_detail(session, item_id, user_id)
            # Reload list after returning (item may have been purchased)


async def _shopping_detail(
    session: "TelnetSession", item_id: str, user_id: str
) -> None:
    """Show detail for one shopping item. BUY marks it purchased."""
    from tangible.models.shopping import ShoppingItem

    engine = session.engine
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    while True:
        with Session() as db:
            item = db.get(ShoppingItem, item_id)
            if item is None:
                return

            coll_name = item.collection.name if item.collection else ""
            linked_title = item.linked_item.title if item.linked_item else None

        if item.purchased_at:
            purchased_str = item.purchased_at.strftime("%Y-%m-%d")
            by_str = item.purchased_by.username if item.purchased_by else "?"
            status_str = f"PURCHASED {purchased_str} by {by_str}"
        else:
            status_str = "PENDING"

        qty_str = f"{item.quantity}"
        if item.unit:
            qty_str += f" {item.unit}"

        screen = Screen(operator=session.username or "")
        screen.title = "SHOPPING — ITEM DETAIL"
        rows = [
            "",
            f"   NAME       : {item.name[:60]}",
            f"   COLLECTION : {coll_name[:60]}",
            f"   TYPE       : {item.list_type}",
            f"   QTY        : {qty_str}",
        ]
        if item.brand:
            rows.append(f"   BRAND      : {item.brand[:60]}")
        if item.notes:
            rows.append(f"   NOTES      : {item.notes[:60]}")
        if linked_title:
            rows.append(f"   LINKED     : {linked_title[:60]}")
        rows.append(f"   STATUS     : {status_str}")
        rows.append("")
        screen.add_rows(rows)

        if item.purchased_at:
            screen.set_hints("0=Back")
            screen.set_prompt("===> ")
        else:
            screen.set_hints("BUY=Mark purchased  0=Back")
            screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        raw = (await _readline(session)).strip().upper()

        if not raw or raw == "0":
            return

        if raw == "BUY" and not item.purchased_at:
            with Session() as db:
                it = db.get(ShoppingItem, item_id)
                if it and not it.purchased_at:
                    it.purchased_at = datetime.now(UTC)
                    it.purchased_by_user_id = user_id
                    db.commit()
            log.info("shopping: user=%s purchased item=%s name=%r",
                     session.username, item_id, item.name)
            # Loop to re-draw detail with updated status

"""Reports workflow — history of completed chores and maintenance tasks.

Commands:
  CHORE   Recent chore completions
  MAINT   Recent maintenance completions
  0       Return to main menu

Both reports show the 60 most recent completions (newest first),
paginated 12 per page.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.orm import sessionmaker

from tangible.retro.command_router import CommandExit
from tangible.retro.layout import Screen, clear_screen

if TYPE_CHECKING:
    from tangible.retro.session import TelnetSession

log = logging.getLogger(__name__)

PAGE_SIZE = 12
HISTORY_LIMIT = 60


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

async def reports_menu(session: "TelnetSession") -> None:
    """Main reports submenu."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "REPORTS"
        screen.add_rows([
            "",
            "   CHORE   Recent chore completion history",
            "   MAINT   Recent maintenance completion history",
            "",
            "   0       Return to main menu",
            "",
        ])
        screen.set_hints("CHORE  MAINT  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd_input = (await _readline(session)).strip().upper()

        if not cmd_input or cmd_input in ("MENU", "BACK", "0"):
            raise CommandExit("menu")

        command = cmd_input.split()[0]

        if command == "CHORE":
            await _chore_history(session)
        elif command == "MAINT":
            await _maint_history(session)


# ---------------------------------------------------------------------------
# Chore history
# ---------------------------------------------------------------------------

async def _chore_history(session: "TelnetSession") -> None:
    from tangible.models.collection import Collection
    from tangible.models.maintenance import Chore, ChoreCompletion
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
                select(ChoreCompletion)
                .join(Chore, ChoreCompletion.chore_id == Chore.id)
                .outerjoin(Collection, Chore.collection_id == Collection.id)
                .where(
                    or_(
                        Collection.id.is_(None) | _auth_filter(u, Collection),
                        Chore.owner_user_id == user_id,
                    )
                )
                .order_by(ChoreCompletion.completed_at.desc())
                .limit(HISTORY_LIMIT)
            ).all()

        total = len(rows)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages - 1)
        start = page * PAGE_SIZE
        slice_ = rows[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = f"REPORTS — CHORE HISTORY  ({total} records)"

        if not slice_:
            screen.add_rows(["", "   No chore completions recorded.", ""])
        else:
            screen.add_rows([""])
            for comp in slice_:
                date_str = comp.completed_at.strftime("%Y-%m-%d")
                chore_name = comp.chore.name[:48] if comp.chore else "(deleted)"
                cost_str = ""
                if comp.cost:
                    cur = comp.currency or ""
                    cost_str = f"  {cur}{comp.cost:.2f}"
                screen.add_rows([f"   {date_str}  {chore_name:<48}{cost_str}"])

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


# ---------------------------------------------------------------------------
# Maintenance history
# ---------------------------------------------------------------------------

async def _maint_history(session: "TelnetSession") -> None:
    from tangible.models.collection import Collection
    from tangible.models.item import Item
    from tangible.models.maintenance import MaintenanceCompletion, MaintenanceTask
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
                select(MaintenanceCompletion)
                .join(MaintenanceTask, MaintenanceCompletion.task_id == MaintenanceTask.id)
                .join(Item, MaintenanceTask.item_id == Item.id)
                .join(Collection, Item.collection_id == Collection.id)
                .where(_auth_filter(u, Collection))
                .order_by(MaintenanceCompletion.completed_at.desc())
                .limit(HISTORY_LIMIT)
            ).all()

        total = len(rows)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, pages - 1)
        start = page * PAGE_SIZE
        slice_ = rows[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = f"REPORTS — MAINT HISTORY  ({total} records)"

        if not slice_:
            screen.add_rows(["", "   No maintenance completions recorded.", ""])
        else:
            screen.add_rows([""])
            for comp in slice_:
                date_str = comp.completed_at.strftime("%Y-%m-%d")
                task_name = comp.task.name[:30] if comp.task else "(deleted)"
                item_title = comp.task.item.title[:28] if (comp.task and comp.task.item) else ""
                cost_str = ""
                if comp.cost:
                    cur = comp.currency or ""
                    cost_str = f"  {cur}{comp.cost:.2f}"
                tech_str = f"  [{comp.technician[:16]}]" if comp.technician else ""
                line = f"   {date_str}  {task_name:<30}  {item_title:<28}{cost_str}{tech_str}"
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

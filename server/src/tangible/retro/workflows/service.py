"""Service desk workflow — chores and maintenance tasks.

Commands (available from the service desk menu):
  CHORE   Browse due/overdue recurring chores; mark complete
  MAINT   Browse due/overdue maintenance tasks; mark complete with details
  0       Return to main menu
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
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


def _due_label(due_at: datetime | None, now: datetime) -> str:
    """Return a terse status string for a due date."""
    if due_at is None:
        return "NO DUE DATE"
    delta = (due_at - now).days
    if delta < 0:
        return f"OVERDUE {abs(delta)}D"
    if delta == 0:
        return "DUE TODAY"
    return f"DUE IN {delta}D"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def service_desk_menu(session: "TelnetSession") -> None:
    """Service desk: CHORE / MAINT dispatch."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "SERVICE DESK"
        screen.add_rows([
            "",
            "   CHORE    Recurring household chores",
            "   MAINT    Item maintenance tasks",
            "",
            "   0        Return to main menu",
            "",
        ])
        screen.set_hints("CHORE=Chores  MAINT=Maintenance  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd = (await _readline(session)).strip().upper()

        if not cmd or cmd in ("0", "MENU", "BACK"):
            raise CommandExit("menu")

        if cmd == "CHORE":
            await _chore_list(session)
        elif cmd == "MAINT":
            await _maint_list(session)
        # Unrecognized: redraw


# ---------------------------------------------------------------------------
# CHORE — recurring chore list and completion
# ---------------------------------------------------------------------------

async def _chore_list(session: "TelnetSession") -> None:
    """Show due/overdue chores, allow select → complete."""
    from tangible.models.collection import Collection
    from tangible.models.maintenance import Chore
    from tangible.models.user import User

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)
    now = datetime.now(UTC)

    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if not user:
            return

        # Chores from user-accessible collections + standalone (owner_user_id)
        rows = db.execute(
            select(
                Chore.id,
                Chore.name,
                Chore.next_due_at,
                Chore.last_completed_at,
                Chore.interval_days,
                Chore.collection_id,
            )
            .outerjoin(Collection, Chore.collection_id == Collection.id)
            .where(
                or_(
                    Chore.owner_user_id == user.id,
                    (Chore.collection_id.isnot(None)) & _auth_filter(user, Collection),
                )
            )
            .order_by(Chore.next_due_at.asc().nullslast())
        ).all()

    if not rows:
        screen = Screen(operator=session.username or "")
        screen.title = "CHORES"
        screen.set_message("NO CHORES FOUND.")
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
        screen.title = f"CHORES  ({total} TOTAL)"
        screen.add_rows([
            "",
            f"   Page {page + 1} of {total_pages}",
            "",
            f"   {'#':<4} {'CHORE NAME':<38} {'STATUS':>14}",
            "   " + "-" * 60,
        ])

        for i, row in enumerate(page_rows, 1):
            name = (row.name or "")[:37].ljust(37)
            status_str = _due_label(row.next_due_at, now).rjust(14)
            screen.add_row(f"   {i:<4} {name}  {status_str}")

        screen.add_row("   " + "-" * 60)

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
                completed = await _chore_detail(session, page_rows[idx].id)
                if completed:
                    # Reload after completion to show updated due dates
                    with Session() as db:
                        user = db.scalar(select(User).where(User.username == session.username))
                        if not user:
                            return
                        rows = db.execute(
                            select(
                                Chore.id, Chore.name, Chore.next_due_at,
                                Chore.last_completed_at, Chore.interval_days,
                                Chore.collection_id,
                            )
                            .outerjoin(Collection, Chore.collection_id == Collection.id)
                            .where(
                                or_(
                                    Chore.owner_user_id == user.id,
                                    (Chore.collection_id.isnot(None)) & _auth_filter(user, Collection),
                                )
                            )
                            .order_by(Chore.next_due_at.asc().nullslast())
                        ).all()
                        total = len(rows)
                        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
                        page = min(page, total_pages - 1)
                        now = datetime.now(UTC)


async def _chore_detail(session: "TelnetSession", chore_id: str) -> bool:
    """Show chore detail and offer COMPLETE. Returns True if completed."""
    from tangible.models.maintenance import Chore, ChoreCompletion
    from tangible.models.base import ulid_str

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)
    now = datetime.now(UTC)

    with Session() as db:
        chore = db.scalar(select(Chore).where(Chore.id == chore_id))
        if not chore:
            return False

        last_done = (
            chore.last_completed_at.strftime("%m/%d/%Y %H:%M") if chore.last_completed_at else "NEVER"
        )
        next_due = (
            chore.next_due_at.strftime("%m/%d/%Y") if chore.next_due_at else "N/A"
        )
        interval = f"{chore.interval_days}D" if chore.interval_days else "N/A"
        status_str = _due_label(chore.next_due_at, now)
        name = chore.name
        notes = chore.notes or "(none)"

    screen = Screen(operator=session.username or "")
    screen.title = "CHORE DETAIL"
    screen.add_rows([
        "",
        f"   {'NAME':<16} {name[:60]}",
        f"   {'LAST DONE':<16} {last_done}",
        f"   {'NEXT DUE':<16} {next_due}",
        f"   {'INTERVAL':<16} {interval}",
        f"   {'STATUS':<16} {status_str}",
        f"   {'NOTES':<16} {notes[:50]}",
        "",
        "   COMPLETE   Mark as done (add notes/cost)",
        "   0          Back",
    ])
    screen.set_hints("COMPLETE=Mark Done  0=Back")
    screen.set_prompt("COMMAND ===> ")

    await session.transport.write(clear_screen() + screen.render())
    cmd = (await _readline(session)).strip().upper()

    if cmd != "COMPLETE":
        return False

    # Gather completion details
    await session.transport.write("\r\n   NOTES (Enter to skip) ===> ")
    comp_notes = (await _readline(session)).strip() or None

    await session.transport.write("   COST (Enter to skip) ===> ")
    cost_str = (await _readline(session)).strip()
    cost: Decimal | None = None
    currency: str | None = None
    if cost_str:
        try:
            cost = Decimal(cost_str)
            await session.transport.write("   CURRENCY (USD) ===> ")
            cur = (await _readline(session)).strip().upper()
            currency = cur if len(cur) == 3 else "USD"
        except InvalidOperation:
            pass  # ignore unparseable cost

    with Session() as db:
        comp = ChoreCompletion(
            id=ulid_str(),
            chore_id=chore_id,
            completed_at=now,
            notes=comp_notes,
            cost=cost,
            currency=currency,
        )
        db.add(comp)

        # Advance next_due_at
        chore = db.scalar(select(Chore).where(Chore.id == chore_id))
        if chore:
            chore.last_completed_at = now
            if chore.interval_days:
                chore.next_due_at = now + timedelta(days=chore.interval_days)
            else:
                chore.next_due_at = None
        db.commit()

        next_due_new = chore.next_due_at.strftime("%m/%d/%Y") if (chore and chore.next_due_at) else "N/A"

    screen = Screen(operator=session.username or "")
    screen.title = "CHORE COMPLETE"
    screen.add_rows([
        "",
        f"   {'COMPLETED':<16} {now.strftime('%m/%d/%Y %H:%M')}",
        f"   {'NEXT DUE':<16} {next_due_new}",
        "",
    ])
    screen.set_message("CHORE MARKED COMPLETE.")
    screen.set_hints("0=Back")
    screen.set_prompt("COMMAND ===> ")
    await session.transport.write(clear_screen() + screen.render())
    await _readline(session)
    return True


# ---------------------------------------------------------------------------
# MAINT — item maintenance task list and completion
# ---------------------------------------------------------------------------

async def _maint_list(session: "TelnetSession") -> None:
    """Show due/overdue maintenance tasks across user-accessible items."""
    from tangible.models.collection import Collection
    from tangible.models.item import Item
    from tangible.models.maintenance import MaintenanceTask
    from tangible.models.user import User

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)
    now = datetime.now(UTC)

    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if not user:
            return

        rows = db.execute(
            select(
                MaintenanceTask.id,
                MaintenanceTask.name,
                MaintenanceTask.next_due_at,
                MaintenanceTask.last_completed_at,
                MaintenanceTask.interval_days,
                Item.title.label("item_title"),
                Item.id.label("item_id"),
            )
            .join(Item, MaintenanceTask.item_id == Item.id)
            .join(Item.collection)
            .where(_auth_filter(user, Collection))
            .order_by(MaintenanceTask.next_due_at.asc().nullslast())
        ).all()

    if not rows:
        screen = Screen(operator=session.username or "")
        screen.title = "MAINTENANCE"
        screen.set_message("NO MAINTENANCE TASKS FOUND.")
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
        screen.title = f"MAINTENANCE  ({total} TOTAL)"
        screen.add_rows([
            "",
            f"   Page {page + 1} of {total_pages}",
            "",
            f"   {'#':<4} {'TASK':<28} {'ITEM':<20} {'STATUS':>12}",
            "   " + "-" * 68,
        ])

        for i, row in enumerate(page_rows, 1):
            task_name = (row.name or "")[:27].ljust(27)
            item_title = (row.item_title or "")[:19].ljust(19)
            status_str = _due_label(row.next_due_at, now).rjust(12)
            screen.add_row(f"   {i:<4} {task_name}  {item_title}  {status_str}")

        screen.add_row("   " + "-" * 68)

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
                completed = await _maint_detail(session, page_rows[idx].id)
                if completed:
                    with Session() as db:
                        user = db.scalar(select(User).where(User.username == session.username))
                        if not user:
                            return
                        rows = db.execute(
                            select(
                                MaintenanceTask.id, MaintenanceTask.name,
                                MaintenanceTask.next_due_at, MaintenanceTask.last_completed_at,
                                MaintenanceTask.interval_days,
                                Item.title.label("item_title"), Item.id.label("item_id"),
                            )
                            .join(Item, MaintenanceTask.item_id == Item.id)
                            .join(Item.collection)
                            .where(_auth_filter(user, Collection))
                            .order_by(MaintenanceTask.next_due_at.asc().nullslast())
                        ).all()
                        total = len(rows)
                        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
                        page = min(page, total_pages - 1)
                        now = datetime.now(UTC)


async def _maint_detail(session: "TelnetSession", task_id: str) -> bool:
    """Show maintenance task detail and offer COMPLETE. Returns True if completed."""
    from tangible.models.item import Item
    from tangible.models.maintenance import MaintenanceCompletion, MaintenanceTask
    from tangible.models.base import ulid_str

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)
    now = datetime.now(UTC)

    with Session() as db:
        task = db.scalar(select(MaintenanceTask).where(MaintenanceTask.id == task_id))
        if not task:
            return False
        item = db.scalar(select(Item).where(Item.id == task.item_id))

        last_done = (
            task.last_completed_at.strftime("%m/%d/%Y %H:%M") if task.last_completed_at else "NEVER"
        )
        next_due = task.next_due_at.strftime("%m/%d/%Y") if task.next_due_at else "N/A"
        interval = f"{task.interval_days}D" if task.interval_days else "N/A"
        status_str = _due_label(task.next_due_at, now)
        task_name = task.name
        item_title = item.title if item else task.item_id
        notes = task.notes or "(none)"

    screen = Screen(operator=session.username or "")
    screen.title = "MAINTENANCE DETAIL"
    screen.add_rows([
        "",
        f"   {'TASK':<16} {task_name[:60]}",
        f"   {'ITEM':<16} {item_title[:60]}",
        f"   {'LAST DONE':<16} {last_done}",
        f"   {'NEXT DUE':<16} {next_due}",
        f"   {'INTERVAL':<16} {interval}",
        f"   {'STATUS':<16} {status_str}",
        f"   {'NOTES':<16} {notes[:50]}",
        "",
        "   COMPLETE   Mark as done (add details)",
        "   0          Back",
    ])
    screen.set_hints("COMPLETE=Mark Done  0=Back")
    screen.set_prompt("COMMAND ===> ")

    await session.transport.write(clear_screen() + screen.render())
    cmd = (await _readline(session)).strip().upper()

    if cmd != "COMPLETE":
        return False

    # Gather completion details
    await session.transport.write("\r\n   NOTES (Enter to skip)       ===> ")
    comp_notes = (await _readline(session)).strip() or None

    await session.transport.write("   COST (Enter to skip)        ===> ")
    cost_str = (await _readline(session)).strip()
    cost: Decimal | None = None
    currency: str | None = None
    if cost_str:
        try:
            cost = Decimal(cost_str)
            await session.transport.write("   CURRENCY (USD)              ===> ")
            cur = (await _readline(session)).strip().upper()
            currency = cur if len(cur) == 3 else "USD"
        except InvalidOperation:
            pass

    await session.transport.write("   TECHNICIAN (Enter to skip)  ===> ")
    technician = (await _readline(session)).strip() or None

    await session.transport.write("   ODOMETER READING (skip)     ===> ")
    odo_str = (await _readline(session)).strip()
    odometer: Decimal | None = None
    if odo_str:
        try:
            odometer = Decimal(odo_str)
        except InvalidOperation:
            pass

    await session.transport.write("   HOURS READING (skip)        ===> ")
    hrs_str = (await _readline(session)).strip()
    hours: Decimal | None = None
    if hrs_str:
        try:
            hours = Decimal(hrs_str)
        except InvalidOperation:
            pass

    with Session() as db:
        from tangible.models.user import User
        user_row = db.scalar(select(User).where(User.username == session.username))
        comp = MaintenanceCompletion(
            id=ulid_str(),
            task_id=task_id,
            completed_at=now,
            notes=comp_notes,
            cost=cost,
            currency=currency,
            technician=technician,
            odometer_reading=odometer,
            hours_reading=hours,
            completed_by_user_id=user_row.id if user_row else None,
        )
        db.add(comp)

        task = db.scalar(select(MaintenanceTask).where(MaintenanceTask.id == task_id))
        if task:
            task.last_completed_at = now
            if task.interval_days:
                task.next_due_at = now + timedelta(days=task.interval_days)
            else:
                task.next_due_at = None
        db.commit()

        next_due_new = task.next_due_at.strftime("%m/%d/%Y") if (task and task.next_due_at) else "N/A"

    screen = Screen(operator=session.username or "")
    screen.title = "MAINTENANCE COMPLETE"
    screen.add_rows([
        "",
        f"   {'COMPLETED':<16} {now.strftime('%m/%d/%Y %H:%M')}",
        f"   {'NEXT DUE':<16} {next_due_new}",
        "",
    ])
    screen.set_message("MAINTENANCE TASK MARKED COMPLETE.")
    screen.set_hints("0=Back")
    screen.set_prompt("COMMAND ===> ")
    await session.transport.write(clear_screen() + screen.render())
    await _readline(session)
    return True

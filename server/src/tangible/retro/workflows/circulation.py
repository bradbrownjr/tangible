"""Circulation desk workflow — loans, returns, active holds.

Commands (available from the circulation menu):
  LOAN  Check out an item to a contact
  RET   Return a checked-out item
  HOLD  Browse active loans / overdue list
  0     Return to main menu
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from tangible.retro.command_router import CommandExit
from tangible.retro.layout import Screen, clear_screen

if TYPE_CHECKING:
    from tangible.retro.session import TelnetSession

log = logging.getLogger(__name__)

PAGE_SIZE = 12
DEFAULT_LOAN_DAYS = 14


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
# Entry point
# ---------------------------------------------------------------------------

async def circulation_menu(session: "TelnetSession") -> None:
    """Circulation desk: LOAN / RET / HOLD dispatch."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "CIRCULATION DESK"
        screen.add_rows([
            "",
            "   LOAN <item>    Check out item to a contact",
            "   RET  <item>    Return a checked-out item",
            "   HOLD            Browse active loans",
            "",
            "   0               Return to main menu",
            "",
        ])
        screen.set_hints("LOAN=Checkout  RET=Return  HOLD=Active  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd_input = (await _readline(session)).strip().upper()

        if not cmd_input or cmd_input in ("0", "MENU", "BACK"):
            raise CommandExit("menu")

        parts = cmd_input.split(maxsplit=1)
        command = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command == "LOAN":
            if not arg:
                await session.transport.write("   ITEM ID ===> ")
                arg = (await _readline(session)).strip()
            if arg:
                await _loan_checkout(session, arg)
        elif command == "RET":
            if not arg:
                await session.transport.write("   ITEM ID ===> ")
                arg = (await _readline(session)).strip()
            if arg:
                await _loan_return(session, arg)
        elif command == "HOLD":
            await _active_loans(session)
        # Unrecognized: redraw menu


# ---------------------------------------------------------------------------
# LOAN — check out an item
# ---------------------------------------------------------------------------

async def _loan_checkout(session: "TelnetSession", item_lookup: str) -> None:
    """Check out an item: find item → check availability → find/pick contact → set due date → commit."""
    from tangible.models.collection import Collection
    from tangible.models.contact import Contact
    from tangible.models.item import Item
    from tangible.models.loan import Loan
    from tangible.models.base import ulid_str
    from tangible.models.user import User

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    # --- Step 1: resolve item ---
    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if not user:
            return

        item = _resolve_item(db, item_lookup, user)
        if not item:
            await _error_screen(session, f"ITEM NOT FOUND: {item_lookup[:40]}")
            return

        # Check for existing active loan
        existing = db.scalar(
            select(Loan).where(Loan.item_id == item.id, Loan.returned_at.is_(None))
        )
        item_id = item.id
        item_title = item.title or item.id
        item_qty = item.quantity

    if existing:
        await _error_screen(session, f"ITEM ALREADY ON LOAN — USE RET TO RETURN FIRST")
        return

    if item_qty < 1:
        await _error_screen(session, f"ITEM QTY IS 0 — CANNOT CHECK OUT")
        return

    # --- Step 2: contact search ---
    contact_id = await _pick_contact(session, user_id=None, engine=session.engine)
    if not contact_id:
        return  # user cancelled

    # --- Step 3: due date ---
    default_due = (datetime.now(UTC) + timedelta(days=DEFAULT_LOAN_DAYS)).strftime("%m/%d/%Y")

    screen = Screen(operator=session.username or "")
    screen.title = "CHECKOUT — DUE DATE"
    screen.add_rows([
        "",
        f"   Item:    {item_title[:60]}",
        f"   Default: {default_due}  ({DEFAULT_LOAN_DAYS} days)",
        "",
        "   Enter due date (MM/DD/YYYY) or press Enter for default.",
        "",
    ])
    screen.set_prompt("DUE DATE ===> ")
    await session.transport.write(clear_screen() + screen.render())

    due_input = (await _readline(session)).strip()
    if due_input:
        due_at = _parse_date(due_input)
        if due_at is None:
            await _error_screen(session, f"INVALID DATE FORMAT — USE MM/DD/YYYY")
            return
    else:
        due_at = datetime.now(UTC) + timedelta(days=DEFAULT_LOAN_DAYS)

    # --- Step 4: notes (optional) ---
    screen = Screen(operator=session.username or "")
    screen.title = "CHECKOUT — NOTES"
    screen.add_rows(["", "   Enter any notes (or press Enter to skip):", ""])
    screen.set_prompt("NOTES ===> ")
    await session.transport.write(clear_screen() + screen.render())
    notes = (await _readline(session)).strip() or None

    # --- Step 5: commit ---
    with Session() as db:
        loan = Loan(
            id=ulid_str(),
            item_id=item_id,
            contact_id=contact_id,
            loaned_at=datetime.now(UTC),
            due_at=due_at,
            notes=notes,
        )
        db.add(loan)
        db.commit()
        loan_id = loan.id

        # Fetch contact name for confirmation
        contact = db.scalar(select(Contact).where(Contact.id == contact_id))
        contact_name = contact.name if contact else contact_id

    screen = Screen(operator=session.username or "")
    screen.title = "CHECKOUT COMPLETE"
    screen.add_rows([
        "",
        f"   Item:      {item_title[:60]}",
        f"   Borrower:  {contact_name}",
        f"   Due:       {due_at.strftime('%m/%d/%Y')}",
        f"   Loan ID:   {loan_id}",
        "",
    ])
    screen.set_message("CHECKOUT RECORDED SUCCESSFULLY.")
    screen.set_hints("0=Back")
    screen.set_prompt("COMMAND ===> ")
    await session.transport.write(clear_screen() + screen.render())
    await _readline(session)


# ---------------------------------------------------------------------------
# RET — return an item
# ---------------------------------------------------------------------------

async def _loan_return(session: "TelnetSession", item_lookup: str) -> None:
    """Return a checked-out item."""
    from tangible.models.collection import Collection
    from tangible.models.contact import Contact
    from tangible.models.item import Item
    from tangible.models.loan import Loan
    from tangible.models.user import User

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if not user:
            return

        item = _resolve_item(db, item_lookup, user)
        if not item:
            await _error_screen(session, f"ITEM NOT FOUND: {item_lookup[:40]}")
            return

        loan = db.scalar(
            select(Loan).where(Loan.item_id == item.id, Loan.returned_at.is_(None))
        )
        if not loan:
            await _error_screen(session, f"NO ACTIVE LOAN FOUND FOR: {item.title[:40]}")
            return

        # Snapshot for confirmation screen
        item_title = item.title or item.id
        loan_id = loan.id
        contact = db.scalar(select(Contact).where(Contact.id == loan.contact_id))
        contact_name = contact.name if contact else loan.contact_id
        due_at = loan.due_at

    # Confirm before committing
    now = datetime.now(UTC)
    overdue = due_at and now > due_at
    overdue_str = f"  *** OVERDUE BY {(now - due_at).days} DAY(S) ***" if overdue else ""

    screen = Screen(operator=session.username or "")
    screen.title = "RETURN ITEM"
    screen.add_rows([
        "",
        f"   Item:      {item_title[:60]}",
        f"   Borrower:  {contact_name}",
        f"   Due:       {due_at.strftime('%m/%d/%Y') if due_at else 'N/A'}{overdue_str}",
        "",
        "   Confirm return?  Y=Yes  N=No",
        "",
    ])
    screen.set_prompt("SELECTION ===> ")
    await session.transport.write(clear_screen() + screen.render())

    confirm = (await _readline(session)).strip().upper()
    if confirm != "Y":
        return

    with Session() as db:
        db.execute(
            update(Loan)
            .where(Loan.id == loan_id)
            .values(returned_at=datetime.now(UTC))
        )
        db.commit()

    screen = Screen(operator=session.username or "")
    screen.title = "RETURN COMPLETE"
    screen.add_rows([
        "",
        f"   Item:      {item_title[:60]}",
        f"   Borrower:  {contact_name}",
        f"   Returned:  {now.strftime('%m/%d/%Y %H:%M')}",
        "",
    ])
    screen.set_message("ITEM RETURNED SUCCESSFULLY.")
    screen.set_hints("0=Back")
    screen.set_prompt("COMMAND ===> ")
    await session.transport.write(clear_screen() + screen.render())
    await _readline(session)


# ---------------------------------------------------------------------------
# HOLD — browse active loans
# ---------------------------------------------------------------------------

async def _active_loans(session: "TelnetSession") -> None:
    """List all active loans with overdue flag; select to view detail."""
    from tangible.models.collection import Collection
    from tangible.models.contact import Contact
    from tangible.models.item import Item
    from tangible.models.loan import Loan
    from tangible.models.user import User

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if not user:
            return

        # All active loans across user-accessible collections
        rows = db.execute(
            select(
                Loan.id,
                Loan.item_id,
                Loan.contact_id,
                Loan.loaned_at,
                Loan.due_at,
                Item.title.label("item_title"),
                Contact.name.label("contact_name"),
            )
            .join(Item, Loan.item_id == Item.id)
            .join(Contact, Loan.contact_id == Contact.id)
            .join(Item.collection)
            .where(
                Loan.returned_at.is_(None),
                _auth_filter(user, Collection),
            )
            .order_by(Loan.due_at.asc().nullslast())
        ).all()

    if not rows:
        screen = Screen(operator=session.username or "")
        screen.title = "ACTIVE LOANS"
        screen.set_message("NO ACTIVE LOANS FOUND.")
        screen.set_hints("0=Back")
        screen.set_prompt("COMMAND ===> ")
        await session.transport.write(clear_screen() + screen.render())
        await _readline(session)
        return

    now = datetime.now(UTC)
    total = len(rows)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = 0

    while True:
        start = page * PAGE_SIZE
        page_rows = rows[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = f"ACTIVE LOANS  ({total} TOTAL)"
        screen.add_rows([
            "",
            f"   Page {page + 1} of {total_pages}",
            "",
            f"   {'#':<4} {'ITEM':<30} {'BORROWER':<18} {'DUE':>10}  {'':4}",
            "   " + "-" * 72,
        ])

        for i, row in enumerate(page_rows, 1):
            title = (row.item_title or "")[:29].ljust(29)
            borrower = (row.contact_name or "")[:17].ljust(17)
            due_str = row.due_at.strftime("%m/%d/%Y") if row.due_at else "  N/A    "
            flag = " OVR" if row.due_at and now > row.due_at else "    "
            screen.add_row(f"   {i:<4} {title}  {borrower}  {due_str}{flag}")

        screen.add_row("   " + "-" * 72)

        nav = []
        if page > 0:
            nav.append("P=PREV")
        if page < total_pages - 1:
            nav.append("N=NEXT")
        nav.append("0=BACK")
        screen.set_hints("  ".join(nav) + "  (OVR=Overdue)")
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
                await _loan_detail(session, page_rows[idx].id)
        # else: redraw


async def _loan_detail(session: "TelnetSession", loan_id: str) -> None:
    """Show detail for a specific loan with return option."""
    from tangible.models.contact import Contact
    from tangible.models.item import Item
    from tangible.models.loan import Loan

    Session = sessionmaker(bind=session.engine, autoflush=False, autocommit=False, future=True)

    with Session() as db:
        loan = db.scalar(select(Loan).where(Loan.id == loan_id))
        if not loan:
            return
        item = db.scalar(select(Item).where(Item.id == loan.item_id))
        contact = db.scalar(select(Contact).where(Contact.id == loan.contact_id))

        now = datetime.now(UTC)
        overdue = loan.due_at and now > loan.due_at
        days_msg = (
            f"OVERDUE {(now - loan.due_at).days} DAY(S)" if overdue
            else f"{(loan.due_at - now).days} DAY(S) REMAINING" if loan.due_at
            else "NO DUE DATE"
        )

        screen = Screen(operator=session.username or "")
        screen.title = "LOAN DETAIL"
        screen.add_rows([
            "",
            f"   {'LOAN ID':<14} {loan.id}",
            f"   {'ITEM':<14} {(item.title if item else loan.item_id)[:60]}",
            f"   {'BORROWER':<14} {contact.name if contact else loan.contact_id}",
            f"   {'LOANED':<14} {loan.loaned_at.strftime('%m/%d/%Y') if loan.loaned_at else 'unknown'}",
            f"   {'DUE':<14} {loan.due_at.strftime('%m/%d/%Y') if loan.due_at else 'N/A'}",
            f"   {'STATUS':<14} {days_msg}",
            f"   {'NOTES':<14} {(loan.notes or '(none)')[:50]}",
            "",
            "   RET    Mark as returned",
            "   0      Back",
        ])
        screen.set_hints("RET=Return  0=Back")
        screen.set_prompt("COMMAND ===> ")

    await session.transport.write(clear_screen() + screen.render())
    cmd = (await _readline(session)).strip().upper()
    if cmd == "RET":
        with Session() as db:
            loan = db.scalar(select(Loan).where(Loan.id == loan_id))
            if loan and item:
                await _loan_return(session, loan.item_id)


# ---------------------------------------------------------------------------
# Contact picker
# ---------------------------------------------------------------------------

async def _pick_contact(session: "TelnetSession", user_id, engine) -> str | None:
    """Search contacts by name; let operator pick one. Returns contact_id or None."""
    from tangible.models.contact import Contact
    from tangible.models.user import User

    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "SELECT BORROWER"
        screen.add_rows([
            "",
            "   Enter name or partial name to search.",
            "   Press Enter with no input to cancel.",
            "",
        ])
        screen.set_prompt("BORROWER ===> ")
        await session.transport.write(clear_screen() + screen.render())

        search = (await _readline(session)).strip()
        if not search:
            return None

        with Session() as db:
            user = db.scalar(select(User).where(User.username == session.username))
            if not user:
                return None
            like = f"%{search}%"
            contacts = db.scalars(
                select(Contact)
                .where(Contact.owner_id == user.id, Contact.name.ilike(like))
                .order_by(Contact.name)
                .limit(PAGE_SIZE)
            ).all()
            # Snapshot while session open
            contact_list = [(c.id, c.name, c.phone or "", c.email or "") for c in contacts]

        if not contact_list:
            screen = Screen(operator=session.username or "")
            screen.title = "SELECT BORROWER"
            screen.set_message(f"NO CONTACTS FOUND: {search[:40]}")
            screen.set_hints("Press Enter to search again")
            screen.set_prompt("BORROWER ===> ")
            await session.transport.write(clear_screen() + screen.render())
            await _readline(session)
            continue

        # Show results
        screen = Screen(operator=session.username or "")
        screen.title = "SELECT BORROWER"
        screen.add_rows(["", f"   {'#':<4} {'NAME':<30} {'PHONE':<16} EMAIL", "   " + "-" * 70])
        for i, (cid, name, phone, email) in enumerate(contact_list, 1):
            screen.add_row(f"   {i:<4} {name[:29]:<29}  {phone[:15]:<15}  {email[:20]}")
        screen.add_row("   " + "-" * 70)
        screen.set_hints("Enter # to select  0=Cancel  S=New Search")
        screen.set_prompt("SELECT # ===> ")
        await session.transport.write(clear_screen() + screen.render())

        choice = (await _readline(session)).strip().upper()
        if choice == "0":
            return None
        elif choice == "S":
            continue
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(contact_list):
                return contact_list[idx][0]
        # else: redraw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_item(db, lookup: str, user):
    """Find an item by ID or barcode within user-accessible collections."""
    from tangible.models.collection import Collection
    from tangible.models.item import Item

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
    return item


def _parse_date(s: str) -> datetime | None:
    """Parse MM/DD/YYYY → timezone-aware UTC datetime. Returns None on failure."""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


async def _error_screen(session: "TelnetSession", msg: str) -> None:
    """Show an error message and wait for keypress."""
    screen = Screen(operator=session.username or "")
    screen.set_message(msg[:78])
    screen.set_hints("Press any key")
    screen.set_prompt("")
    await session.transport.write(clear_screen() + screen.render())
    await _readline(session)

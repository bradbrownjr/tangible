"""Receiving workflow — add new items to a collection.

Commands:
  ADD     Add a new item (prompts for fields interactively)
  0       Return to main menu

Template auto-selection:
  0 templates in collection → skip attrs entirely (generic item)
  1 template               → apply silently, no user prompt
  2+ templates             → show a short curated picker (Vinyl / CD / Cassette…)

After the standard fields the workflow prompts for each template field in
sequence. All fields are optional unless marked required. After committing
the operator is returned to the ADD prompt to add another item without
menu bouncing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from tangible.models.base import ulid_str
from tangible.retro.command_router import CommandExit
from tangible.retro.layout import Screen, clear_screen

if TYPE_CHECKING:
    from tangible.retro.session import TelnetSession

log = logging.getLogger(__name__)

PAGE_SIZE = 12

_CONDITIONS = ("NEW", "GOOD", "FAIR", "POOR", "DAMAGED")


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

async def receiving_menu(session: "TelnetSession") -> None:
    """Main receiving submenu."""
    while True:
        screen = Screen(operator=session.username or "")
        screen.title = "RECEIVING"
        screen.add_rows([
            "",
            "   ADD    Add a new item to a collection",
            "",
            "   0      Return to main menu",
            "",
        ])
        screen.set_hints("ADD=New item  0=Main")
        screen.set_prompt("COMMAND ===> ")

        await session.transport.write(clear_screen() + screen.render())
        cmd_input = (await _readline(session)).strip().upper()

        if not cmd_input or cmd_input in ("MENU", "BACK", "0"):
            raise CommandExit("menu")

        parts = cmd_input.split(maxsplit=1)
        command = parts[0]

        if command == "ADD":
            await _add_item(session)
        # unknown input — just re-draw the menu


# ---------------------------------------------------------------------------
# ADD flow
# ---------------------------------------------------------------------------

async def _add_item(session: "TelnetSession") -> None:
    """Interactively gather item fields and commit to DB.

    Loops back to a fresh ADD prompt after a successful commit so the
    operator can add multiple items without returning to the menu.
    """
    from tangible.models.collection import Collection
    from tangible.models.item import Item
    from tangible.models.item_template import ItemTemplate
    from tangible.models.location import Location
    from tangible.models.user import User

    engine = session.engine
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    # Resolve the user once at the top.
    with Session() as db:
        user = db.scalar(select(User).where(User.username == session.username))
        if user is None:
            return
        user_id = user.id

    # Fetch accessible collections for selection.
    with Session() as db:
        u = db.get(User, user_id)
        colls = db.scalars(
            select(Collection)
            .where(_auth_filter(u, Collection))
            .order_by(Collection.name)
        ).all()

    if not colls:
        await _error_screen(session, "No collections accessible.")
        return

    # Main add loop — keeps running until the operator exits.
    while True:
        # --- Collection selection -----------------------------------------
        coll_id = await _pick_collection(session, colls)
        if coll_id is None:
            return  # operator exited back to receiving menu

        # Load locations and templates for this collection.
        with Session() as db:
            locations = db.scalars(
                select(Location)
                .where(Location.collection_id == coll_id)
                .order_by(Location.name)
            ).all()
            templates = db.scalars(
                select(ItemTemplate)
                .where(ItemTemplate.collection_id == coll_id)
                .order_by(ItemTemplate.name)
            ).all()

        loc_names: dict[str, str] = {loc.name.upper(): loc.id for loc in locations}

        # --- Template auto-selection -------------------------------------
        # 0 → no attrs; 1 → silent; 2+ → short curated picker
        tmpl_id: str | None = None
        tmpl_fields: list[dict] = []
        tmpl_name: str = ""

        if len(templates) == 1:
            tmpl_id = templates[0].id
            tmpl_fields = list(templates[0].fields or [])
            tmpl_name = templates[0].name
        elif len(templates) > 1:
            chosen = await _pick_template(session, templates)
            if chosen is None:
                return
            tmpl_id = chosen.id
            tmpl_fields = list(chosen.fields or [])
            tmpl_name = chosen.name

        # --- Standard field prompts --------------------------------------
        title = await _prompt_required(
            session,
            "TITLE ===> ",
            "Title is required.  Enter a name for this item."
        )
        if title is None:
            return

        # Quantity (default 1)
        qty_raw = await _prompt_optional(session, "QTY (1) ===> ")
        if qty_raw is None:
            return
        try:
            qty = int(qty_raw) if qty_raw else 1
            if qty < 1:
                qty = 1
        except ValueError:
            qty = 1

        # Location (optional, match by name case-insensitive)
        location_id: str | None = None
        if loc_names:
            loc_input = await _prompt_optional(session, "LOCATION (Enter to skip) ===> ")
            if loc_input is None:
                return
            if loc_input:
                location_id = loc_names.get(loc_input.strip().upper())

        # Condition (optional)
        cond_raw = await _prompt_optional(
            session,
            f"CONDITION ({'/'.join(_CONDITIONS)}, Enter=skip) ===> "
        )
        if cond_raw is None:
            return
        condition: str | None = None
        if cond_raw:
            c = cond_raw.strip().upper()
            if c in _CONDITIONS:
                condition = c

        # Barcode — skip if template has its own barcode/isbn/upc field
        tmpl_field_keys = {f["key"] for f in tmpl_fields}
        barcode: str | None = None
        if not tmpl_field_keys.intersection({"barcode", "isbn", "upc"}):
            barcode_raw = await _prompt_optional(session, "BARCODE (Enter to skip) ===> ")
            if barcode_raw is None:
                return
            barcode = barcode_raw.strip() or None

        # Notes (optional)
        notes_raw = await _prompt_optional(session, "NOTES (Enter to skip) ===> ")
        if notes_raw is None:
            return
        notes = notes_raw.strip() or None

        # --- Template-specific field prompts -----------------------------
        attrs: dict[str, Any] = {}
        if tmpl_fields:
            result = await _prompt_template_fields(session, tmpl_fields, tmpl_name)
            if result is None:
                return
            attrs = result

        # --- Confirmation screen -----------------------------------------
        coll_name = next((c.name for c in colls if c.id == coll_id), coll_id)
        confirm = await _confirm_screen(
            session,
            coll_name=coll_name,
            tmpl_name=tmpl_name,
            title=title,
            qty=qty,
            location=next((l.name for l in locations if l.id == location_id), None) if location_id else None,
            condition=condition,
            barcode=barcode,
            notes=notes,
            attrs=attrs,
            tmpl_fields=tmpl_fields,
        )
        if confirm is None:
            return  # exit
        if not confirm:
            continue  # loop back, re-pick collection

        # --- Commit -------------------------------------------------------
        identifiers: dict = {}
        if barcode:
            identifiers["barcode"] = barcode
        # Surface template barcode-like fields into identifiers too
        for key in ("barcode", "isbn", "upc"):
            if key in attrs and attrs[key]:
                identifiers[key] = attrs[key]

        new_item = Item(
            id=ulid_str(),
            collection_id=coll_id,
            title=title,
            quantity=qty,
            location_id=location_id,
            condition=condition,
            notes=notes,
            identifiers=identifiers,
            template_id=tmpl_id,
            attrs=attrs,
        )

        with Session() as db:
            db.add(new_item)
            db.commit()
            saved_id = new_item.id

        log.info("receiving: user=%s added item=%s title=%r tmpl=%s",
                 session.username, saved_id, title, tmpl_id)

        await _success_screen(session, title, saved_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _pick_collection(
    session: "TelnetSession",
    colls: list,
) -> str | None:
    """Show a numbered list of collections; return the chosen ID or None."""
    page = 0
    total = len(colls)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    while True:
        start = page * PAGE_SIZE
        slice_ = colls[start : start + PAGE_SIZE]

        screen = Screen(operator=session.username or "")
        screen.title = "RECEIVING — SELECT COLLECTION"

        rows = []
        for i, coll in enumerate(slice_, start=1):
            rows.append(f"   {i:2}.  {coll.name[:70]}")
        screen.add_rows(rows)

        nav = []
        if page > 0:
            nav.append("P=Prev")
        if page < pages - 1:
            nav.append("N=Next")
        nav.append("0=Cancel")
        screen.set_hints("  ".join(nav))
        screen.set_prompt(f"SELECT (1-{len(slice_)}) ===> ")

        await session.transport.write(clear_screen() + screen.render())
        raw = (await _readline(session)).strip().upper()

        if not raw or raw == "0":
            return None
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
            return slice_[idx].id


async def _pick_template(session: "TelnetSession", templates: list) -> Any | None:
    """Short curated picker for 2+ templates. Returns template object or None."""
    screen = Screen(operator=session.username or "")
    screen.title = "RECEIVING — ITEM TYPE"
    rows = ["", "   Select the type that best describes this item:", ""]
    for i, t in enumerate(templates, start=1):
        rows.append(f"   {i:2}.  {t.name[:70]}")
    rows.append("")
    screen.add_rows(rows)
    screen.set_hints("0=Cancel")
    screen.set_prompt(f"TYPE (1-{len(templates)}) ===> ")

    await session.transport.write(clear_screen() + screen.render())
    raw = (await _readline(session)).strip().upper()

    if not raw or raw == "0":
        return None
    try:
        idx = int(raw) - 1
    except ValueError:
        return None
    if 0 <= idx < len(templates):
        return templates[idx]
    return None


async def _prompt_template_fields(
    session: "TelnetSession",
    fields: list[dict],
    tmpl_name: str,
) -> dict[str, Any] | None:
    """Prompt for each template field. Returns attrs dict or None on cancel (0/BACK)."""
    attrs: dict[str, Any] = {}

    for field in fields:
        key = field.get("key", "")
        label = field.get("label", key)
        ftype = field.get("type", "text")
        required = field.get("required", False)
        options: list[str] = field.get("options", [])

        if ftype == "select" and options:
            val = await _prompt_select(session, label, options, required)
        elif ftype == "boolean":
            val = await _prompt_boolean(session, label)
        elif ftype == "number":
            val = await _prompt_number(session, label, required)
        elif ftype == "date":
            val = await _prompt_date_field(session, label, required)
        else:  # text / url / anything else
            if required:
                raw = await _prompt_required(session, f"{label} ===> ")
                val = raw  # None = cancelled, str = value
            else:
                raw = await _prompt_optional(session, f"{label} (Enter to skip) ===> ")
                val = raw  # None = 0/BACK (cancel), '' = Enter (skip), str = value

        # None always means the user hit 0/BACK → cancel the whole add
        if val is None:
            return None

        # '' (empty string) means the user pressed Enter to skip
        if val == "" or val is False and not required:
            # Store False for boolean fields even when skipped? No — skip means omit.
            # But if required boolean, False is a valid answer.
            pass
        if val not in ("", None):
            attrs[key] = val

    return attrs


async def _prompt_select(
    session: "TelnetSession",
    label: str,
    options: list[str],
    required: bool,
) -> Any | None:
    """Show numbered options for a select field. Returns value, '' (skip), or None (cancel)."""
    while True:
        await session.transport.writeln(f"\r\n   {label}:")
        for i, opt in enumerate(options, start=1):
            await session.transport.writeln(f"      {i}. {opt}")
        skip_hint = "" if required else "  Enter=skip"
        await session.transport.write(f"   SELECT (1-{len(options)}){skip_hint} ===> ")
        raw = (await _readline(session)).strip()

        if not raw:
            if required:
                continue
            return ""  # skip

        if raw.upper() in ("0", "BACK", "CANCEL"):
            return None

        try:
            idx = int(raw) - 1
        except ValueError:
            continue

        if 0 <= idx < len(options):
            return options[idx]


async def _prompt_boolean(session: "TelnetSession", label: str) -> Any | None:
    """Y/N prompt. Returns True, False, '' (skip), or None (cancel)."""
    await session.transport.write(f"   {label} (Y/N, Enter=skip) ===> ")
    raw = (await _readline(session)).strip().upper()
    if not raw:
        return ""  # skip
    if raw in ("0", "BACK", "CANCEL"):
        return None
    if raw in ("Y", "YES"):
        return True
    if raw in ("N", "NO"):
        return False
    return ""  # unrecognized → skip


async def _prompt_number(
    session: "TelnetSession",
    label: str,
    required: bool,
) -> Any | None:
    """Numeric prompt. Returns int/float, '' (skip), or None (cancel)."""
    while True:
        skip_hint = "" if required else " (Enter to skip)"
        await session.transport.write(f"   {label}{skip_hint} ===> ")
        raw = (await _readline(session)).strip()
        if not raw:
            if required:
                continue
            return ""  # skip
        if raw.upper() in ("0", "BACK", "CANCEL"):
            return None
        try:
            # Return int if whole number, else float
            f = float(raw)
            return int(f) if f == int(f) else f
        except ValueError:
            continue


async def _prompt_date_field(
    session: "TelnetSession",
    label: str,
    required: bool,
) -> Any | None:
    """Date prompt (YYYY or MM/DD/YYYY accepted). Returns string value, '' or None."""
    while True:
        skip_hint = "" if required else " (Enter to skip)"
        await session.transport.write(f"   {label} (YYYY){skip_hint} ===> ")
        raw = (await _readline(session)).strip()
        if not raw:
            if required:
                continue
            return ""
        if raw.upper() in ("0", "BACK", "CANCEL"):
            return None
        # Accept year-only or full date; store as-is (display string)
        return raw


async def _prompt_required(
    session: "TelnetSession",
    prompt: str,
    hint: str = "",
) -> str | None:
    """Prompt until a non-empty value is entered. Return None on 0/BACK/empty+hint."""
    while True:
        await session.transport.write(f"   {prompt}")
        raw = (await _readline(session)).strip()
        if not raw:
            if hint:
                await session.transport.writeln(f"\r\n   *** {hint}")
            continue
        if raw.upper() in ("0", "BACK", "CANCEL"):
            return None
        return raw


async def _prompt_optional(
    session: "TelnetSession",
    prompt: str,
) -> str | None:
    """Prompt for an optional field. Returns '' on skip (Enter), None on 0/BACK."""
    await session.transport.write(f"   {prompt}")
    raw = (await _readline(session)).strip()
    if raw.upper() in ("0", "BACK", "CANCEL"):
        return None
    return raw


async def _confirm_screen(
    session: "TelnetSession",
    *,
    coll_name: str,
    tmpl_name: str,
    title: str,
    qty: int,
    location: str | None,
    condition: str | None,
    barcode: str | None,
    notes: str | None,
    attrs: dict[str, Any],
    tmpl_fields: list[dict],
) -> bool | None:
    """Show a review screen. Y=commit, N=re-enter, 0=cancel."""
    screen = Screen(operator=session.username or "")
    screen.title = "RECEIVING — CONFIRM NEW ITEM"

    rows: list[str] = [""]
    rows.append(f"   COLLECTION : {coll_name[:58]}")
    if tmpl_name:
        rows.append(f"   TYPE       : {tmpl_name[:58]}")
    rows.append(f"   TITLE      : {title[:58]}")
    rows.append(f"   QTY        : {qty}")
    rows.append(f"   LOCATION   : {location or '(none)'}")
    rows.append(f"   CONDITION  : {condition or '(none)'}")
    if barcode:
        rows.append(f"   BARCODE    : {barcode}")
    if notes:
        rows.append(f"   NOTES      : {notes[:58]}")

    # Show filled template attrs (label: value), up to remaining work rows
    if attrs and tmpl_fields:
        label_map = {f["key"]: f["label"] for f in tmpl_fields}
        for key, val in attrs.items():
            if val in ("", None):
                continue
            lbl = label_map.get(key, key)
            display = "Yes" if val is True else ("No" if val is False else str(val))
            rows.append(f"   {lbl[:12].upper():<12} : {display[:46]}")
            if len(rows) >= 16:  # leave room for separator + hints + prompt
                break

    rows.append("")
    screen.add_rows(rows)
    screen.set_hints("Y=Add item  N=Re-enter  0=Cancel")
    screen.set_prompt("CONFIRM ===> ")

    await session.transport.write(clear_screen() + screen.render())
    raw = (await _readline(session)).strip().upper()

    if raw == "Y":
        return True
    if raw == "N":
        return False
    return None


async def _success_screen(session: "TelnetSession", title: str, item_id: str) -> None:
    """Show a brief success confirmation, then drop back to ADD prompt."""
    screen = Screen(operator=session.username or "")
    screen.title = "RECEIVING — ITEM ADDED"
    screen.add_rows([
        "",
        f"   ADDED: {title[:64]}",
        f"   ID:    {item_id}",
        "",
        "   Press Enter to add another, or 0 to return to the menu.",
        "",
    ])
    screen.set_hints("Enter=Add another  0=Menu")
    screen.set_prompt("===> ")

    await session.transport.write(clear_screen() + screen.render())
    raw = (await _readline(session)).strip().upper()
    if raw == "0":
        raise CommandExit("menu")
    # anything else (including Enter) → fall through, loop continues


async def _error_screen(session: "TelnetSession", msg: str) -> None:
    screen = Screen(operator=session.username or "")
    screen.title = "RECEIVING — ERROR"
    screen.add_rows(["", f"   ERROR: {msg}", ""])
    screen.set_hints("Press Enter to continue")
    screen.set_prompt("===> ")
    await session.transport.write(clear_screen() + screen.render())
    await _readline(session)

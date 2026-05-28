"""Terminal rendering helpers for the Telnet interface.

Targets an 80-column monochrome terminal (IBM 3270 / VT100 aesthetic).
All ANSI escapes used here are supported by vintage VT100-compatible clients.
"""

from __future__ import annotations

import math
from datetime import datetime

WIDTH = 80


def clear_screen() -> str:
    return "\x1b[2J\x1b[H"


def bold(text: str) -> str:
    return f"\x1b[1m{text}\x1b[0m"


def reverse(text: str) -> str:
    return f"\x1b[7m{text}\x1b[0m"


def center(text: str, width: int = WIDTH) -> str:
    return text.center(width)


def hr(char: str = "-", width: int = WIDTH) -> str:
    return char * width


def box_top(title: str = "", width: int = WIDTH) -> str:
    """Return the top border of a box, with an optional centred title."""
    if title:
        inner = width - 4  # 2 for corners, 2 for spaces
        title_str = f" {title[:inner]} "
        pad = inner - len(title_str)
        left = pad // 2
        right = pad - left
        return "+" + "-" * left + title_str + "-" * right + "+"
    return "+" + "-" * (width - 2) + "+"


def box_bottom(width: int = WIDTH) -> str:
    return "+" + "-" * (width - 2) + "+"


def box_row(text: str = "", width: int = WIDTH) -> str:
    inner = width - 2
    return "| " + text[:inner - 2].ljust(inner - 2) + " |"


def status_bar(operator: str, date: datetime | None = None, terminal: str = "001") -> str:
    """Return the top status bar line."""
    now = date or datetime.now()
    date_str = now.strftime("%m/%d/%Y")
    left = f"  TANGIBLE IMS         OPERATOR: {operator[:16].upper()}"
    right = f"TERM: {terminal}  DATE: {date_str}  "
    gap = WIDTH - len(left) - len(right)
    return left + " " * max(1, gap) + right


def table_header(*cols: tuple[str, int]) -> str:
    """cols = [(heading, width), ...]. Returns header + divider lines."""
    header = "|"
    divider = "+"
    for heading, w in cols:
        header += f" {heading[:w].ljust(w)} |"
        divider += "-" * (w + 2) + "+"
    return divider + "\n" + header + "\n" + divider


def table_row(*cells: tuple[str, int]) -> str:
    """cells = [(value, width), ...]. Returns a single data row."""
    row = "|"
    for val, w in cells:
        row += f" {str(val)[:w].ljust(w)} |"
    return row


def table_footer(*cols: tuple[str, int]) -> str:
    divider = "+"
    for _, w in cols:
        divider += "-" * (w + 2) + "+"
    return divider


def paginate(items: list, page: int, per_page: int = 20) -> tuple[list, int]:
    """Return (page_items, total_pages)."""
    total = len(items)
    total_pages = max(1, math.ceil(total / per_page))
    start = page * per_page
    return items[start : start + per_page], total_pages


def pagination_prompt(page: int, total_pages: int) -> str:
    parts = []
    if page > 0:
        parts.append("[P]rev")
    if page < total_pages - 1:
        parts.append("[N]ext")
    parts.append("[B]ack")
    return "  " + "  ".join(parts) + "  ENTER SELECTION: "


def main_menu_screen(operator: str) -> str:
    lines = [
        clear_screen(),
        box_top(width=WIDTH),
        box_row(status_bar(operator), width=WIDTH),
        box_bottom(width=WIDTH),
        "",
        center("TANGIBLE INVENTORY MANAGEMENT SYSTEM"),
        center("DEPARTMENT STORE EDITION"),
        "",
        hr(),
        "",
        "          MAIN MENU",
        "          ---------",
        "",
        "          1.  BROWSE INVENTORY",
        "          2.  SEARCH ITEMS",
        "          3.  ITEM LOOKUP (ID / BARCODE / UPC)",
        "          4.  ADD NEW ITEM",
        "          5.  EDIT ITEM",
        "          6.  COLLECTIONS",
        "          7.  SHOPPING LISTS",
        "          8.  TASKS",
        "          9.  CHORES",
        "          10. MAINTENANCE",
        "          11. LOCATIONS",
        "          12. LOANS",
        "          0.  SIGN OUT",
        "",
        hr(),
        "",
        "          ENTER SELECTION: ",
    ]
    return "\r\n".join(lines)


def login_screen() -> str:
    lines = [
        clear_screen(),
        box_top(width=WIDTH),
        box_row(center("TANGIBLE INVENTORY MANAGEMENT SYSTEM"), width=WIDTH),
        box_row(center("DEPARTMENT STORE EDITION"), width=WIDTH),
        box_bottom(width=WIDTH),
        "",
        center(f"{'':->40}"),
        "",
        "   Please log in to access the system.",
        "",
    ]
    return "\r\n".join(lines)

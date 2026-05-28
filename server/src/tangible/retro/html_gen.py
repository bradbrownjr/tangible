"""HTML 1.0-compatible page generation helpers.

Rules:
- No CSS (no <STYLE>, no style= attributes)
- No JavaScript (no <SCRIPT>)
- No <DIV>, no <SPAN>
- No named character entities beyond the handful HTML 1.0 defines
- Tables, forms, anchors, images, headings, lists, preformatted text only
- Every page includes a plain-text navigation bar at the top

All functions return bytes (UTF-8) so they can be written to the asyncio
transport directly.
"""

from __future__ import annotations

import html
from io import BytesIO


def _e(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text), quote=True)


def page(title: str, body: str, nav_user: str | None = None) -> bytes:
    """Wrap ``body`` HTML in a complete HTML 1.0 document."""
    nav = _nav_bar(nav_user)
    doc = (
        "<HTML>\n"
        "<HEAD><TITLE>" + _e(title) + " - Tangible IMS</TITLE></HEAD>\n"
        "<BODY>\n"
        + nav
        + "<H2>" + _e(title) + "</H2>\n"
        + body
        + "\n<HR>\n"
        "<P><SMALL>Tangible Inventory Management System</SMALL></P>\n"
        "</BODY>\n"
        "</HTML>\n"
    )
    return doc.encode("utf-8")


def _nav_bar(user: str | None) -> str:
    parts = [
        '<A HREF="/">Home</A>',
        '<A HREF="/collections">Collections</A>',
        '<A HREF="/search">Search</A>',
        '<A HREF="/lists">Lists</A>',
        '<A HREF="/tasks">Tasks</A>',
        '<A HREF="/chores">Chores</A>',
        '<A HREF="/maintenance">Maintenance</A>',
        '<A HREF="/locations">Locations</A>',
        '<A HREF="/loans">Loans</A>',
        '<A HREF="/stores">Stores</A>',
    ]
    if user:
        parts.append(f"[{_e(user)}]")
        parts.append('<A HREF="/logout">Logout</A>')
    return "<P>" + " | ".join(parts) + "</P>\n<HR>\n"


def error_page(title: str, message: str) -> bytes:
    body = f"<P><B>{_e(message)}</B></P>\n<P><A HREF=\"/\">Return to Home</A></P>"
    return page(title, body)


def redirect_response(location: str) -> bytes:
    """HTTP/1.0 redirect body — caller must send the header."""
    return (
        "<HTML><HEAD><TITLE>Redirect</TITLE></HEAD>"
        f'<BODY><P>Redirecting to <A HREF="{_e(location)}">{_e(location)}</A></P></BODY></HTML>\n'
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def table_start(headers: list[str]) -> str:
    cells = "".join(f"<TH>{_e(h)}</TH>" for h in headers)
    return "<TABLE BORDER=1>\n<TR>" + cells + "</TR>\n"


def table_row(cells: list[str]) -> str:
    tds = "".join(f"<TD>{c}</TD>" for c in cells)
    return "<TR>" + tds + "</TR>\n"


def table_end() -> str:
    return "</TABLE>\n"


# ---------------------------------------------------------------------------
# Form helpers
# ---------------------------------------------------------------------------

def form_start(action: str, method: str = "POST") -> str:
    return f'<FORM ACTION="{_e(action)}" METHOD="{method}">\n'


def form_end() -> str:
    return "</FORM>\n"


def input_text(name: str, label: str, value: str = "", size: int = 40) -> str:
    return (
        f"<P>{_e(label)}: "
        f'<INPUT TYPE="TEXT" NAME="{_e(name)}" VALUE="{_e(value)}" SIZE={size}></P>\n'
    )


def input_hidden(name: str, value: str) -> str:
    return f'<INPUT TYPE="HIDDEN" NAME="{_e(name)}" VALUE="{_e(value)}">\n'


def input_textarea(name: str, label: str, value: str = "", rows: int = 4, cols: int = 50) -> str:
    return (
        f"<P>{_e(label)}:<BR>\n"
        f'<TEXTAREA NAME="{_e(name)}" ROWS={rows} COLS={cols}>{_e(value)}</TEXTAREA></P>\n'
    )


def input_submit(label: str = "Submit") -> str:
    return f'<P><INPUT TYPE="SUBMIT" VALUE="{_e(label)}"></P>\n'


def select_field(name: str, label: str, options: list[tuple[str, str]], selected: str = "") -> str:
    """Build a <SELECT> drop-down. options = [(value, display_label), ...]."""
    opts = ""
    for val, disp in options:
        sel = " SELECTED" if val == selected else ""
        opts += f'<OPTION VALUE="{_e(val)}"{sel}>{_e(disp)}</OPTION>\n'
    return f"<P>{_e(label)}:\n<SELECT NAME=\"{_e(name)}\">\n{opts}</SELECT></P>\n"


# ---------------------------------------------------------------------------
# Pagination helpers
# ---------------------------------------------------------------------------

def pagination_links(base_url: str, page: int, total: int, per_page: int) -> str:
    """Return prev/next links for paginated lists."""
    parts: list[str] = []
    if page > 0:
        parts.append(f'<A HREF="{_e(base_url)}?page={page - 1}">[Prev]</A>')
    if (page + 1) * per_page < total:
        parts.append(f'<A HREF="{_e(base_url)}?page={page + 1}">[Next]</A>')
    if not parts:
        return ""
    return "<P>" + " ".join(parts) + f" (showing {page * per_page + 1}-{min((page + 1) * per_page, total)} of {total})</P>\n"


# ---------------------------------------------------------------------------
# Image helper — converts a stored photo to GIF bytes via Pillow
# ---------------------------------------------------------------------------

def photo_to_gif(photo_path: str, max_width: int = 320, max_height: int = 240) -> bytes | None:
    """Read a stored photo file and return GIF bytes, or None on failure."""
    try:
        from PIL import Image

        with Image.open(photo_path) as img:
            img = img.convert("RGB")
            img.thumbnail((max_width, max_height), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="GIF")
            return buf.getvalue()
    except Exception:
        return None


def photo_to_jpeg(photo_path: str, max_width: int = 320, max_height: int = 240) -> bytes | None:
    """Read a stored photo file and return JPEG bytes, or None on failure."""
    try:
        from PIL import Image

        with Image.open(photo_path) as img:
            img = img.convert("RGB")
            img.thumbnail((max_width, max_height), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=75)
            return buf.getvalue()
    except Exception:
        return None

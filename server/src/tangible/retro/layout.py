"""Terminal layout primitives for 80x24 green-screen UI.

Supports: status bar (row 1), title (row 2), work area (rows 4-20),
message/error line (row 22), command hints (row 23), input prompt (row 24).
"""

from __future__ import annotations

from datetime import datetime

WIDTH = 80
HEIGHT = 24
# Usable rows for work area: rows 4-20 = 17 rows (including borders/separators)
WORK_ROWS = 17

class Screen:
    """Composable terminal screen builder for fixed 24-row layout."""

    def __init__(self, operator: str = "", title: str = ""):
        self.operator = operator
        self.title = title
        self.work_lines: list[str] = []
        self.message: str = ""
        self.hints: str = ""
        self.prompt: str = "COMMAND ===> "

    def add_row(self, text: str) -> None:
        """Add a line to the work area."""
        self.add_rows([text])

    def add_rows(self, lines: list[str]) -> None:
        """Add multiple lines to the work area, capped at WORK_ROWS."""
        for line in lines:
            if len(self.work_lines) < WORK_ROWS:
                self.work_lines.append(line[:WIDTH])

    def set_message(self, msg: str) -> None:
        """Set the message/error line (row 22)."""
        self.message = msg[:WIDTH]

    def set_hints(self, hints: str) -> None:
        """Set the command hints line (row 23)."""
        self.hints = hints[:WIDTH]

    def set_prompt(self, prompt: str) -> None:
        """Set the input prompt (row 24)."""
        self.prompt = prompt[:WIDTH]

    def render(self) -> str:
        """Render the full 24-row screen."""
        lines = []
        
        # Row 1: Status bar (date refreshed at render time)
        now = datetime.now()
        date_str = now.strftime("%m/%d/%Y")
        left = f"  TANGIBLE IMS         OPERATOR: {self.operator[:16].upper()}"
        right = f"TERM: 001  DATE: {date_str}  "
        gap = WIDTH - len(left) - len(right)
        status = left + " " * max(1, gap) + right
        lines.append(status[:WIDTH])
        
        # Row 2: Title
        title_line = self.title.center(WIDTH)
        lines.append(title_line[:WIDTH])
        
        # Row 3: separator
        lines.append("-" * WIDTH)
        
        # Rows 4-20: Work area (17 rows)
        for i in range(WORK_ROWS):
            if i < len(self.work_lines):
                lines.append(self.work_lines[i])
            else:
                lines.append("")
        
        # Row 21: separator
        lines.append("-" * WIDTH)
        
        # Row 22: Message/error line
        lines.append(self.message)
        
        # Row 23: Command hints
        lines.append(self.hints)
        
        # Row 24: Input prompt + cursor indicator
        lines.append(self.prompt)
        
        # Ensure exactly 24 lines
        while len(lines) < HEIGHT:
            lines.append("")
        return "\r\n".join(lines[:HEIGHT])


def clear_screen() -> str:
    """Clear screen and reset cursor (xterm + VT100 compatible)."""
    return "\x1b[H\x1b[2J\x1b[3J"


def bold(text: str) -> str:
    """Bold text."""
    return f"\x1b[1m{text}\x1b[0m"


def reverse(text: str) -> str:
    """Reverse video (inverted colors)."""
    return f"\x1b[7m{text}\x1b[0m"


def center(text: str, width: int = WIDTH) -> str:
    """Center text."""
    return text.center(width)


def pad_left(text: str, width: int) -> str:
    """Left-align and pad to width."""
    return text[:width].ljust(width)


def pad_right(text: str, width: int) -> str:
    """Right-align and pad to width."""
    return str(text)[-width:].rjust(width)


def hr(char: str = "-", width: int = WIDTH) -> str:
    """Horizontal rule."""
    return char * width


def key_value_pane(items: list[tuple[str, str]], label_width: int = 20, value_width: int = 58) -> list[str]:
    """Generate key-value display lines (e.g., for item detail screen).
    
    items: list of (label, value) tuples
    label_width: width for label column (right-aligned label)
    value_width: width for value column (left-aligned value)
    
    Returns list of display lines, each exactly WIDTH chars.
    """
    lines = []
    for label, value in items:
        label_str = pad_right(label + ":", label_width)
        value_str = pad_left(value, value_width)
        line = label_str + value_str
        lines.append(line[:WIDTH])
    return lines


def dense_table(headers: list[tuple[str, int]], rows: list[tuple[str, ...]], max_rows: int = 12) -> list[str]:
    """Generate dense table output (optimized for narrow terminals).
    
    headers: list of (header_label, column_width) tuples
    rows: list of row data tuples (must match header count)
    max_rows: max rows to display (recommended 12 for 24-row screen)
    
    Returns list of display lines (header + divider + data rows).
    """
    lines = []
    
    # Header divider
    divider = ""
    for _, width in headers:
        divider += "+" + "-" * (width + 2)
    divider += "+"
    lines.append(divider[:WIDTH])
    
    # Header row
    header = "|"
    for label, width in headers:
        header += " " + pad_left(label, width) + " |"
    lines.append(header[:WIDTH])
    
    # Data divider
    lines.append(divider[:WIDTH])
    
    # Data rows (capped at max_rows)
    for i, row in enumerate(rows[:max_rows]):
        data_row = "|"
        for j, (_, width) in enumerate(headers):
            cell = str(row[j] if j < len(row) else "")
            data_row += " " + pad_left(cell, width) + " |"
        lines.append(data_row[:WIDTH])
    
    # Footer divider
    lines.append(divider[:WIDTH])
    
    return lines


def message_box(msg: str, width: int = WIDTH) -> str:
    """Format an error or info message in a box."""
    msg = msg[:width - 4]
    return f"  *** {msg} ***"


def input_line(prompt: str = "COMMAND ===> ") -> str:
    """Format the input prompt line."""
    return prompt[:WIDTH]

"""Terminal display helpers: colored text, table formatting, box drawing."""

from __future__ import annotations

import os
import sys
from typing import Optional


# ─── ANSI Color Codes ──────────────────────────────────────────────────────────

class Color:
    """ANSI escape codes for terminal colors and styles."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


def _color_enabled() -> bool:
    """Check if color output should be enabled."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


COLORS_ENABLED = _color_enabled()


def colorize(text: str, *codes: str) -> str:
    """Apply ANSI color codes to text.

    Args:
        text: The text to colorize.
        *codes: ANSI escape codes to apply.

    Returns:
        Colorized string, or plain text if colors are disabled.
    """
    if not COLORS_ENABLED or not codes:
        return text
    prefix = "".join(codes)
    return f"{prefix}{text}{Color.RESET}"


def bold(text: str) -> str:
    """Make text bold."""
    return colorize(text, Color.BOLD)


def dim(text: str) -> str:
    """Make text dim."""
    return colorize(text, Color.DIM)


def green(text: str) -> str:
    """Make text green (for positive values)."""
    return colorize(text, Color.BRIGHT_GREEN)


def red(text: str) -> str:
    """Make text red (for negative values)."""
    return colorize(text, Color.BRIGHT_RED)


def yellow(text: str) -> str:
    """Make text yellow (for warnings/highlights)."""
    return colorize(text, Color.BRIGHT_YELLOW)


def cyan(text: str) -> str:
    """Make text cyan (for headers)."""
    return colorize(text, Color.BRIGHT_CYAN)


def blue(text: str) -> str:
    """Make text blue."""
    return colorize(text, Color.BRIGHT_BLUE)


def magenta(text: str) -> str:
    """Make text magenta."""
    return colorize(text, Color.BRIGHT_MAGENTA)


def white_bold(text: str) -> str:
    """Make text bright white and bold."""
    return colorize(text, Color.BRIGHT_WHITE, Color.BOLD)


def color_odds(odds_str: str) -> str:
    """Colorize an odds string: green for +, red for -."""
    if odds_str.startswith("+"):
        return green(odds_str)
    elif odds_str.startswith("-"):
        return red(odds_str)
    return odds_str


def color_pnl(value: float) -> str:
    """Colorize a P&L value: green for positive, red for negative."""
    if value > 0:
        return green(f"+${value:,.2f}")
    elif value < 0:
        return red(f"-${abs(value):,.2f}")
    else:
        return dim(f"$0.00")


# ─── Box Drawing Characters ───────────────────────────────────────────────────

class Box:
    """Unicode box-drawing characters for table borders."""

    # Corners
    TL = "\u250c"  # top-left
    TR = "\u2510"  # top-right
    BL = "\u2514"  # bottom-left
    BR = "\u2518"  # bottom-right

    # T-junctions
    T_DOWN = "\u252c"  # top with down
    T_UP = "\u2534"   # bottom with up
    T_RIGHT = "\u251c"  # left with right
    T_LEFT = "\u2524"  # right with left

    # Cross
    CROSS = "\u253c"

    # Lines
    H = "\u2500"  # horizontal
    V = "\u2502"  # vertical

    # Double lines (for emphasis)
    DH = "\u2550"  # double horizontal
    DV = "\u2551"  # double vertical

    # Rounded corners (for softer look)
    RTL = "\u256d"
    RTR = "\u256e"
    RBL = "\u2570"
    RBR = "\u256f"


def _visible_len(s: str) -> int:
    """Get the visible length of a string, ignoring ANSI escape codes.

    Args:
        s: String potentially containing ANSI codes.

    Returns:
        Visible character count.
    """
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    return len(ansi_escape.sub('', s))


def _pad(s: str, width: int, align: str = "left") -> str:
    """Pad a string to a given width, accounting for ANSI codes.

    Args:
        s: String to pad (may contain ANSI codes).
        width: Desired visible width.
        align: 'left', 'right', or 'center'.

    Returns:
        Padded string.
    """
    visible = _visible_len(s)
    padding = max(0, width - visible)

    if align == "right":
        return " " * padding + s
    elif align == "center":
        left_pad = padding // 2
        right_pad = padding - left_pad
        return " " * left_pad + s + " " * right_pad
    else:
        return s + " " * padding


def render_table(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    alignments: Optional[list[str]] = None,
    col_padding: int = 1,
    indent: int = 2,
) -> str:
    """Render a beautiful bordered table with box-drawing characters.

    Args:
        title: Table title displayed in the header.
        headers: Column header strings.
        rows: List of row data (each row is a list of strings).
        alignments: Per-column alignment ('left', 'right', 'center').
            Defaults to 'left' for all columns.
        col_padding: Padding on each side of cell content.
        indent: Left indentation in spaces.

    Returns:
        Formatted table string ready for printing.
    """
    num_cols = len(headers)

    if alignments is None:
        alignments = ["left"] * num_cols

    # Calculate column widths (max visible width per column)
    col_widths = []
    for i in range(num_cols):
        max_w = _visible_len(headers[i])
        for row in rows:
            if i < len(row):
                max_w = max(max_w, _visible_len(row[i]))
        col_widths.append(max_w + col_padding * 2)

    # Ensure title fits
    inner_width = sum(col_widths) + num_cols - 1  # cols + separators
    title_visible = _visible_len(title)
    if title_visible + 4 > inner_width:
        # Expand last column to fit title
        extra = (title_visible + 4) - inner_width
        col_widths[-1] += extra
        inner_width = sum(col_widths) + num_cols - 1

    pad = " " * indent
    lines: list[str] = []

    # ── Top border ──
    top_line = Box.TL + (Box.H * inner_width) + Box.TR
    lines.append(pad + dim(top_line))

    # ── Title row ──
    title_text = _pad(bold(cyan(title)), inner_width, "center")
    lines.append(pad + dim(Box.V) + title_text + dim(Box.V))

    # ── Header separator ──
    header_sep_parts = [Box.H * w for w in col_widths]
    header_sep = Box.T_RIGHT + (Box.T_DOWN.join(header_sep_parts)) + Box.T_LEFT
    lines.append(pad + dim(header_sep))

    # ── Header row ──
    header_cells = []
    for i, h in enumerate(headers):
        cell_text = _pad(bold(h), col_widths[i] - col_padding * 2, alignments[i])
        header_cells.append(" " * col_padding + cell_text + " " * col_padding)
    header_line = dim(Box.V) + dim(Box.V).join(header_cells) + dim(Box.V)
    lines.append(pad + header_line)

    # ── Header/body separator ──
    sep_parts = [Box.H * w for w in col_widths]
    body_sep = Box.T_RIGHT + (Box.CROSS.join(sep_parts)) + Box.T_LEFT
    lines.append(pad + dim(body_sep))

    # ── Data rows ──
    for row in rows:
        cells = []
        for i in range(num_cols):
            val = row[i] if i < len(row) else ""
            cell_text = _pad(val, col_widths[i] - col_padding * 2, alignments[i])
            cells.append(" " * col_padding + cell_text + " " * col_padding)
        row_line = dim(Box.V) + dim(Box.V).join(cells) + dim(Box.V)
        lines.append(pad + row_line)

    # ── Bottom border ──
    bottom_parts = [Box.H * w for w in col_widths]
    bottom_line = Box.BL + (Box.T_UP.join(bottom_parts)) + Box.BR
    lines.append(pad + dim(bottom_line))

    return "\n".join(lines)


def render_box(title: str, content_lines: list[str], indent: int = 2) -> str:
    """Render a simple box with title and content lines.

    Args:
        title: Box title.
        content_lines: Lines of content to display.
        indent: Left indentation in spaces.

    Returns:
        Formatted box string.
    """
    # Calculate width
    max_content = max((_visible_len(line) for line in content_lines), default=20)
    title_len = _visible_len(title)
    width = max(max_content + 4, title_len + 6, 30)

    pad = " " * indent
    lines: list[str] = []

    # Top border
    lines.append(pad + dim(Box.TL + Box.H * width + Box.TR))

    # Title
    title_text = _pad(bold(cyan(title)), width, "center")
    lines.append(pad + dim(Box.V) + title_text + dim(Box.V))

    # Separator
    lines.append(pad + dim(Box.T_RIGHT + Box.H * width + Box.T_LEFT))

    # Content lines
    for line in content_lines:
        content_padded = "  " + _pad(line, width - 2, "left")
        lines.append(pad + dim(Box.V) + content_padded + dim(Box.V))

    # Bottom border
    lines.append(pad + dim(Box.BL + Box.H * width + Box.BR))

    return "\n".join(lines)


def render_footer(parts: list[str], indent: int = 2) -> str:
    """Render a subtle footer line.

    Args:
        parts: Text parts to join with centered dots.
        indent: Left indentation.

    Returns:
        Formatted footer string.
    """
    pad = " " * indent
    separator = dim("  \u00b7  ")
    footer = separator.join(dim(p) for p in parts)
    return f"\n{pad}{footer}\n"


def print_banner() -> str:
    """Return the odds-cli ASCII banner."""
    banner = f"""
  {bold(cyan("odds-cli"))} {dim("v0.1.0")}
  {dim("Check live sports odds from your terminal")}
"""
    return banner


def star_marker() -> str:
    """Return a highlighted star marker for best lines."""
    return yellow("\u2605")

"""The program name in ASCII art at the top of windows that stay open for a while.

Shown once per process by Setup, the dev tools and the first-time installation of Python or
packages. The font is data/fonts/future.tlf; its license is listed in LICENSE.md.
"""

from __future__ import annotations

import shutil

from backend.DONT_CHANGE.backend_settings import BANNER_FONT_PATH
from backend.DONT_CHANGE.scripts.config import settings

_shown = False
HARD_BLANK = "\x7f"  # how the font marks a space that belongs to a character


def load_font():
    """Return {character: rows} of the banner font (a TOIlet file)."""
    with open(BANNER_FONT_PATH, encoding="utf-8", errors="replace") as stream:
        lines = stream.read().splitlines()
    fields = lines[0][6:].split()
    height, comment_lines = int(fields[0]), int(fields[4])
    position = 1 + comment_lines
    glyphs = {}

    def read_glyph():
        nonlocal position
        rows = lines[position : position + height]
        if len(rows) < height:
            return None
        position += height
        end_mark = rows[-1][-1:] if rows[-1] else ""
        return [row.rstrip(end_mark) if end_mark else row for row in rows]

    # Required characters: ASCII 32..126, then the German characters FIGlet always defines.
    for code in [*range(32, 127), 196, 214, 220, 228, 246, 252, 223]:
        rows = read_glyph()
        if rows is None:
            break
        glyphs[chr(code)] = rows
    # Code-tagged characters: a line "code [comment]", then the rows.
    while position < len(lines):
        tag = lines[position].split(None, 1)
        position += 1
        if not tag:
            continue
        try:
            code = int(tag[0], 0)
        except ValueError:
            continue
        rows = read_glyph()
        if rows is None:
            break
        if code >= 0:
            glyphs[chr(code)] = rows
    return glyphs


def render(text: str) -> list:
    """The rows of text in the banner font; characters the font lacks are left out."""
    glyphs = load_font()
    height = len(next(iter(glyphs.values())))
    result = [""] * height
    for character in text:
        rows = glyphs.get(character)
        if rows is None:
            continue
        width = max(len(row) for row in rows)
        result = [line + row.ljust(width) for line, row in zip(result, rows)]
    result = [line.replace(HARD_BLANK, " ") for line in result]
    while result and not result[-1].strip():
        result.pop()
    while result and not result[0].strip():
        result.pop(0)
    return [line.rstrip() for line in result]


def print_banner() -> None:
    """Print the program name in the banner font, once per process; never raises."""
    global _shown
    if _shown:
        return
    _shown = True
    try:
        s = settings()
        rows = render(s.program_name)
        columns = shutil.get_terminal_size((120, 30)).columns
        if not rows or max(len(row) for row in rows) >= columns:
            rows = [s.program_name, "=" * len(s.program_name)]  # too wide for the window
        print("\n".join(rows) + "\n", flush=True)
    except Exception:
        from backend.DONT_CHANGE.scripts.diagnostics import note_ignored

        note_ignored("print_banner")


def show_setup_window() -> None:
    """Show this console (shortcuts may start it minimized) with the banner on top."""
    from backend.DONT_CHANGE.scripts.console_tools import show_console

    show_console()
    print_banner()

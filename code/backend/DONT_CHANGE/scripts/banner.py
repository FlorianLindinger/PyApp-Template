"""The program name in ASCII art at the top of windows that stay open for a while.

Shown once per process by Setup, the dev tools and the first-time installation of Python or
packages; the font is app_name_banner_font in developer_settings.py (None: no banner). Fonts are
FIGlet (.flf) and TOIlet (.tlf) files in data/fonts; their licenses are listed in LICENSE.md.
"""

from __future__ import annotations

import os
import shutil

from backend.DONT_CHANGE.backend_settings import FONTS_DIR
from backend.DONT_CHANGE.scripts.config import settings

_shown = False


def font_path(name: str) -> str:
    for extension in (".flf", ".tlf"):
        path = os.path.join(FONTS_DIR, name + extension)
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(f'Font "{name}" not found in {FONTS_DIR}')


def load_font(path: str):
    """Return (hardblank, {character: rows}) of a FIGlet/TOIlet font file and whether it kerns."""
    with open(path, encoding="utf-8", errors="replace") as stream:
        lines = stream.read().splitlines()
    header = lines[0]
    if header[:5] not in ("flf2a", "tlf2a"):
        raise ValueError(f"{path} is not a FIGlet or TOIlet font")
    hardblank = header[5] if len(header) > 5 and header[5] != " " else ""
    fields = header[6:].split()
    height, old_layout, comment_lines = int(fields[0]), int(fields[3]), int(fields[4])
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
    return hardblank, glyphs, old_layout != -1


def render(text: str, path: str) -> list:
    """The rows of text in the font; characters the font lacks are left out."""
    hardblank, glyphs, kerning = load_font(path)
    height = len(next(iter(glyphs.values())))
    result = [""] * height
    for character in text:
        rows = glyphs.get(character)
        if rows is None:
            continue
        width = max(len(row) for row in rows)
        rows = [row.ljust(width) for row in rows]
        if kerning and any(result):
            # Move the glyph left until it touches the text so far (FIGlet "fitting").
            overlap = min(
                (len(line) - len(line.rstrip(" "))) + (len(row) - len(row.lstrip(" ")))
                for line, row in zip(result, rows)
            )
            overlap = min(overlap, width, min(len(line) for line in result))
            merged = []
            for line, row in zip(result, rows):
                keep, shared = line[: len(line) - overlap], line[len(line) - overlap :]
                shared = "".join(b if a == " " else a for a, b in zip(shared, row[:overlap]))
                merged.append(keep + shared + row[overlap:])
            result = merged
        else:
            result = [line + row for line, row in zip(result, rows)]
    if hardblank:
        result = [line.replace(hardblank, " ") for line in result]
    while result and not result[-1].strip():
        result.pop()
    while result and not result[0].strip():
        result.pop(0)
    return [line.rstrip() for line in result]


def print_banner() -> None:
    """Print the program name in the configured font, once per process; never raises."""
    global _shown
    if _shown:
        return
    _shown = True
    try:
        s = settings()
        if not s.app_name_banner_font:
            return
        rows = render(s.program_name, font_path(s.app_name_banner_font))
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

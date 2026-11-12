"""The program name in ASCII art at the top of windows that stay open for a while.

Shown once per process by Setup, the dev tools and the first-time installation of Python or
packages. The font is data/fonts/pyapp-grid.tlf.
"""

from __future__ import annotations

import shutil
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

from pyapp.DONT_CHANGE.backend_settings import BANNER_FONT_PATH
from pyapp.DONT_CHANGE.scripts.config import settings

_shown = False
HARD_BLANK = "\x7f"  # how the font marks a space that belongs to a character


def load_font() -> Dict[str, List[str]]:
    """Return {character: rows} of the banner font (a TOIlet file)."""
    with Path(BANNER_FONT_PATH).open(encoding="utf-8", errors="replace") as stream:
        lines = stream.read().splitlines()
    fields = lines[0][6:].split()
    height, comment_lines = int(fields[0]), int(fields[4])
    position = 1 + comment_lines
    glyphs = {}

    def read_glyph() -> Optional[List[str]]:
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


def render(text: str) -> List[str]:
    """The rows of text in the banner font; characters the font lacks are left out."""
    glyphs = load_font()
    height = len(next(iter(glyphs.values())))
    result = [""] * height
    for character in unicodedata.normalize("NFC", text):
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


# Fonts of the classic console that have every block character of the banner font; Windows 11
# ships them. Consolas, its default, lacks the quadrants (U+2596-U+259F).
BLOCK_FONTS = ("Cascadia Mono", "Cascadia Code")


def font_has_glyphs(face: str, text: str) -> bool:
    """True when the installed font `face` has a glyph for every character of text (GDI)."""
    import ctypes
    from ctypes import wintypes

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wintypes.DWORD] * 8 + [wintypes.LPCWSTR]
    gdi32.CreateFontW.restype = wintypes.HFONT
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.GetTextFaceW.argtypes = [wintypes.HDC, ctypes.c_int, wintypes.LPWSTR]
    gdi32.GetGlyphIndicesW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    gdi32.GetGlyphIndicesW.restype = wintypes.DWORD
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    dc = gdi32.CreateCompatibleDC(None)
    font = gdi32.CreateFontW(-16, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, face)  # 1: DEFAULT_CHARSET
    try:
        gdi32.SelectObject(dc, font)
        # GDI silently substitutes another font for one that is not installed.
        selected = ctypes.create_unicode_buffer(64)
        gdi32.GetTextFaceW(dc, 64, selected)
        if selected.value.lower() != face.lower():
            return False
        indices = (wintypes.WORD * len(text))()
        gdi32.GetGlyphIndicesW(dc, text, len(text), indices, 1)  # 1: GGI_MARK_NONEXISTING_GLYPHS
        return all(index != 0xFFFF for index in indices)
    finally:
        gdi32.DeleteObject(font)
        gdi32.DeleteDC(dc)


def console_can_show(text: str) -> bool:
    """Make sure this console can display text: in a classic console window whose font lacks
    glyphs, switch it to a font that has them. False when that is not possible.

    Windows Terminal, the browser terminal and redirected output fall back to other fonts for
    missing glyphs themselves, so only the classic console (conhost) is changed.
    """
    import ctypes
    from ctypes import wintypes

    class _ConsoleFont(ctypes.Structure):  # CONSOLE_FONT_INFOEX
        _fields_ = (
            ("cbSize", wintypes.ULONG),
            ("nFont", wintypes.DWORD),
            ("dwFontSize", wintypes._COORD),
            ("FontFamily", wintypes.UINT),
            ("FontWeight", wintypes.UINT),
            ("FaceName", wintypes.WCHAR * 32),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    hwnd = int(kernel32.GetConsoleWindow() or 0)
    name = ctypes.create_unicode_buffer(64)
    ctypes.windll.user32.GetClassNameW(hwnd, name, 64)
    if not hwnd or name.value != "ConsoleWindowClass":
        return True
    output = kernel32.GetStdHandle(-11)
    info = _ConsoleFont()
    info.cbSize = ctypes.sizeof(_ConsoleFont)
    if not kernel32.GetCurrentConsoleFontEx(output, False, ctypes.byref(info)):
        return True  # stdout is not this console (redirected)
    if font_has_glyphs(info.FaceName, text):
        return True
    for face in BLOCK_FONTS:
        if font_has_glyphs(face, text):
            info.FaceName = face
            info.nFont = 0
            return bool(kernel32.SetCurrentConsoleFontEx(output, False, ctypes.byref(info)))
    return False


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
        plain = [s.program_name, "=" * len(s.program_name)]
        if not rows or max(len(row) for row in rows) >= columns:
            rows = plain  # too wide for the window
        elif not _can_show("".join({character for row in rows for character in row if ord(character) > 127})):
            rows = plain  # the window's font would show the block characters as boxes
        print("\n".join(rows) + "\n", flush=True)
    except Exception:
        from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

        note_ignored("print_banner")


def _can_show(text: str) -> bool:
    """console_can_show(text), but a failing check never costs the banner: then it is printed as before."""
    if not text:
        return True
    try:
        return console_can_show(text)
    except Exception:
        from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

        note_ignored("banner: console font check")
        return True


def show_setup_window() -> None:
    """Show this console (shortcuts may start it minimized) with the banner on top."""
    from pyapp.DONT_CHANGE.scripts.console_tools import show_console

    show_console()
    print_banner()

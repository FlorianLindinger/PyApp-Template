"""Console output of the development tools, with the same look as the launcher's own windows.

Standalone on purpose (not scripts/console_tools.py): verify_launcher must keep working while the
launcher code it checks is broken.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Tuple

HEADING = "\x1b[1;36m"  # bold cyan
GOOD = "\x1b[1;37;42m"  # white on green
WARNING = "\x1b[1;30;43m"  # black on yellow
ERROR = "\x1b[1;37;41m"  # white on red
DIM = "\x1b[90m"  # grey
RESET = "\x1b[0m"


def use_utf8(stream: object) -> None:
    """The rules and markers below do not exist in the legacy code pages used for redirected output.

    Decided by the encoding, not isatty(): Windows reports the NUL device as a terminal, but Python
    only uses UTF-8 for real consoles, so "> nul" (or /dev/null) would otherwise crash.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None and (getattr(stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
        reconfigure(encoding="utf-8", errors="replace")


for _stream in (sys.stdout, sys.stderr):
    use_utf8(_stream)

_console_prepared = False
_progress_shown = False


def run(main: Callable[[], Optional[int]]) -> Optional[int]:
    """Run a tool: problems it expects become a short message, programming errors keep their traceback."""
    try:
        return main()
    except KeyboardInterrupt:
        warn("Stopped with Ctrl+C.")
        return 130
    except (OSError, RuntimeError) as problem:  # includes timeouts and missing files
        error(problem)
        return 1


def _interactive() -> bool:
    return bool(sys.stdout is not None and sys.stdout.isatty())


def interactive() -> bool:
    """A person watches in a terminal (not an editor's Git output or a redirected file)."""
    return _interactive()


def done(label: str, ok: bool, seconds: float, note: str = "") -> None:
    """One finished step: "  ✓ label   1.2 s" (✗ in red when it failed)."""
    mark = styled("✓", "\x1b[32m") if ok else styled("✗", "\x1b[31m")
    _say(f"  {mark} {label.ljust(34)} {styled(f'{seconds:4.1f} s', DIM)}" + (f"  {styled(note, DIM)}" if note else ""))


def _prepare_console() -> None:
    """The classic Windows console only understands colors after this switch."""
    global _console_prepared
    if _console_prepared or os.name != "nt":
        return
    _console_prepared = True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except (AttributeError, OSError):
        pass  # plain escape codes are only a cosmetic problem


def styled(text: object, style: str) -> str:
    """Color only for an interactive console; redirected output stays plain."""
    if not _interactive():
        return str(text)
    _prepare_console()
    return f"{style}{text}{RESET}"


def _say(text: str = "") -> None:
    global _progress_shown
    if _progress_shown:
        print("\r\x1b[K", end="")
        _progress_shown = False
    print(text, flush=True)


def _badge(label: str, style: str, message: object) -> None:
    lines = str(message).split("\n")
    indent = " " * (len(label) + 3)
    _say("\n".join([styled(f" {label} ", style) + " " + lines[0]] + [indent + line for line in lines[1:]]))


def blank_line() -> None:
    _say()


def heading(title: str, width: int = 72) -> None:
    """A section: a blank line, then "── title ───"."""
    _say()
    _say(styled(f"── {title} " + "─" * max(3, width - len(title) - 4), HEADING))


def step(message: object) -> None:
    """Something that may take a while."""
    _say(styled("»", HEADING) + " " + str(message))


def info(message: object) -> None:
    _say(styled(message, DIM))


def success(message: object) -> None:
    _badge("OK", GOOD, message)


def warn(message: object) -> None:
    _badge("!", WARNING, message)


def error(message: object) -> None:
    _badge("ERROR", ERROR, message)


def progress(message: object) -> None:
    """Replace the previous progress text; nothing is printed when the output is redirected."""
    global _progress_shown
    if _interactive():
        _prepare_console()
        print("\r\x1b[K" + styled(message, DIM), end="", flush=True)
        _progress_shown = True


def file_link(path: Path, line: Optional[int] = None) -> str:
    """A link that opens the file, at the line if given: "file:///D:/x/app.py#L12".

    VS Code makes these clickable (Ctrl+click) in "Show Command Output", where a plain
    "app.py:12" is only text; its terminal, Windows Terminal and browsers open them too.
    """
    return path.resolve().as_uri() + (f"#L{line}" if line else "")


def fields(rows: Iterable[Tuple[str, object]], indent: int = 2) -> None:
    """Aligned "label   value" rows."""
    rows = list(rows)
    width = max((len(label) for label, _ in rows), default=0)
    for label, value in rows:
        _say(" " * indent + styled(label.ljust(width), DIM) + "  " + str(value))


def table(headers: Sequence[str], rows: Iterable[Sequence[object]], indent: int = 2) -> None:
    """Columns as wide as their content; every column but the last is aligned right."""
    text_rows = [[str(cell) for cell in row] for row in rows]
    widths = [max([len(header)] + [len(row[i]) for row in text_rows]) for i, header in enumerate(headers)]

    def line(cells: Sequence[str]) -> str:
        parts = [cell.rjust(width) for cell, width in zip(cells[:-1], widths)]
        return " " * indent + "  ".join([*parts, cells[-1]])

    _say(styled(line(headers), DIM))
    for row in text_rows:
        _say(line(row))

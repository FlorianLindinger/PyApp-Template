"""For programs running inside the browser terminal: change the page's icon and colors; the palette.

A pseudoconsole passes text, titles and VT sequences, but not a window icon or the classic
console's `color` command. The host therefore names an append-only file in an environment
variable (ENV_VAR unless configured otherwise); every request is one JSON line appended to it,
which also works with several writing processes.

    from browser_terminal import ui
    if ui.inside():
        ui.request(icon=r"C:\\path\\success.ico", colors=ui.colors_from_code("2F"))

Cheap to import: standard library only, no Windows calls at import time.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

ENV_VAR = "BROWSER_TERMINAL_UI"

# The classic console's 16 colors (Windows' "Campbell" scheme), by the digit `color` uses.
CONSOLE_COLORS = {
    "0": "#0C0C0C",
    "1": "#0037DA",
    "2": "#13A10E",
    "3": "#3A96DD",
    "4": "#C50F1F",
    "5": "#881798",
    "6": "#C19C00",
    "7": "#CCCCCC",
    "8": "#767676",
    "9": "#3B78FF",
    "A": "#16C60C",
    "B": "#61D6D6",
    "C": "#E74856",
    "D": "#B4009E",
    "E": "#F9F1A5",
    "F": "#F2F2F2",
}

# The same palette in xterm.js's order of the ANSI colors, with the classic console's defaults.
DEFAULT_THEME = {
    "background": "#0C0C0C",
    "foreground": "#CCCCCC",
    "cursor": "#CCCCCC",
    "selectionBackground": "#FFFFFF55",
    "black": "#0C0C0C",
    "red": "#C50F1F",
    "green": "#13A10E",
    "yellow": "#C19C00",
    "blue": "#0037DA",
    "magenta": "#881798",
    "cyan": "#3A96DD",
    "white": "#CCCCCC",
    "brightBlack": "#767676",
    "brightRed": "#E74856",
    "brightGreen": "#16C60C",
    "brightYellow": "#F9F1A5",
    "brightBlue": "#3B78FF",
    "brightMagenta": "#B4009E",
    "brightCyan": "#61D6D6",
    "brightWhite": "#F2F2F2",
}


def colors_from_code(code: str) -> Dict[str, str]:
    """Background and text color from a `color` argument ("9F"; one digit is the text color; "" the defaults)."""
    code = (code or "07").upper()
    if len(code) == 1:
        code = "0" + code
    return {"background": CONSOLE_COLORS[code[0]], "foreground": CONSOLE_COLORS[code[1]]}


def inside(env_var: str = ENV_VAR) -> bool:
    """True in a console shown by the browser terminal.

    The variable alone is not enough: a process in it may open a console window of its own
    (CREATE_NEW_CONSOLE), which inherits the variable, so the console must be a pseudoconsole.
    """
    if not os.environ.get(env_var):
        return False
    import ctypes

    hwnd = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
    name = ctypes.create_unicode_buffer(64)
    ctypes.windll.user32.GetClassNameW(hwnd, name, 64)
    return bool(hwnd) and name.value == "PseudoConsoleWindow"


def request(
    env_var: str = ENV_VAR,
    icon: Optional[str] = None,
    colors: Optional[Dict[str, str]] = None,
    notify: Optional[str] = None,
    failed: bool = False,
    waiting_for_input: bool = False,
) -> None:
    """Ask the page for a new icon (.ico or .png file) and/or colors ({"background", "foreground"}).

    notify: how the program ended (e.g. "main.py failed: ..."); the page shows it as a desktop
    notification if the user switched those on and is looking elsewhere.
    waiting_for_input: the program is about to read input (the page can come to the front).
    """
    fields: Dict[str, object] = {}
    if icon is not None:
        fields["icon"] = icon
    if colors is not None:
        fields["colors"] = colors
    if notify:
        fields["notify"] = notify
        fields["failed"] = failed
    if waiting_for_input:
        fields["input"] = True
    with Path(os.environ[env_var]).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(fields) + "\n")

"""The browser terminal's stable address and its start link (pyapp-template://).

Address: http://<name>.localhost:<port>/<key>/ stays the same for this copy of the project, so
it can be bookmarked; it works while the program runs. The port is derived from the project's
taskbar identity (program name and folder), the key is a random secret kept per PC in
generated/ (not committed), so other users of the PC cannot open the terminal.

Start link: Setup registers the URL scheme for the current Windows user (HKCU, no admin rights),
so a link or bookmark "<scheme>://start" starts the program in the browser terminal, also when
it is not running. Only registrations made by a PyApp launcher are changed or removed.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import secrets
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Optional, Tuple, Union

from pyapp.DONT_CHANGE.backend_settings import (
    BROWSER_KEY_PATH,
    CONHOST_EXE,
    LAUNCHER_BROWSER_TERMINAL,
)

Settings = Union[ModuleType, SimpleNamespace]

# Ports derived from the project identity: above the usual service ports, below Windows'
# dynamic range (49152+), which other programs get at random.
PORT_RANGE = (20000, 40000)
# browser_terminal_address: "http://<name>.localhost:<port>" or "http://127.0.0.1:<port>".
ADDRESS_PATTERN = re.compile(r"http://((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*localhost|127\.0\.0\.1):(\d{1,5})/?")
# Marks the scheme's registry key as made by a PyApp launcher (the value is its B.bat).
LAUNCHER_MARKER = "PyAppLauncher"


def address_problem(value: object) -> Optional[str]:
    """Why browser_terminal_address is unusable, or None."""
    if value == "":
        return None
    match = ADDRESS_PATTERN.fullmatch(value) if isinstance(value, str) else None
    if not match:
        return 'use "" or an address like "http://my-app.localhost:8765" or "http://127.0.0.1:8765"'
    if not 1024 <= int(match.group(2)) <= 65535:
        return "use a port from 1024 to 65535"
    return None


def _name_part(app_id: str) -> str:
    """The readable part of the taskbar identity ("pyapp-template" of "pyapp-template.573ed3245a")."""
    return app_id.split(".", 1)[0] or "pyapp"


def address(s: Settings, app_id: str) -> Tuple[str, int, str]:
    """(host name, port, key) of the browser terminal of this copy of the project."""
    configured = ADDRESS_PATTERN.fullmatch(s.browser_terminal_address or "")
    if configured:
        host, port = configured.group(1), int(configured.group(2))
    else:
        host = _name_part(app_id) + ".localhost"
        low, high = PORT_RANGE
        port = low + int(hashlib.sha256(app_id.encode("utf-8")).hexdigest()[:8], 16) % (high - low)
    return host, port, key()


def key() -> str:
    """The secret part of the address, created on first use and kept for this PC."""
    path = Path(BROWSER_KEY_PATH)
    try:
        existing = path.read_text(encoding="utf-8").strip()
        if re.fullmatch(r"[A-Za-z0-9_-]{16,}", existing):
            return existing
    except OSError:
        pass
    value = secrets.token_urlsafe(18)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="utf-8")
    return value


def page_url(s: Settings, app_id: str) -> str:
    host, port, secret = address(s, app_id)
    return f"http://{host}:{port}/{secret}/"


# ---------------------------------------------------------------- start link


def scheme(app_id: str) -> str:
    """The URL scheme of the start link: the readable part of the taskbar identity."""
    return _name_part(app_id)


def _key_path(name: str) -> str:
    return "Software\\Classes\\" + name


def registered_launcher(name: str) -> Optional[str]:
    """The B.bat a PyApp launcher registered for the scheme, "" for a scheme of another program, None if free."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _key_path(name)) as handle:
            try:
                return str(winreg.QueryValueEx(handle, LAUNCHER_MARKER)[0])
            except OSError:
                return ""
    except OSError:
        return None


def register_start_link(name: str, app_id: str, icon: str) -> bool:
    """Register <name>:// to start the browser terminal shortcut's launcher; False if another program owns it.

    The registration of another copy of this program is replaced: the last Setup wins, as for
    the Start Menu folder.
    """
    import winreg

    if registered_launcher(name) == "":
        return False
    command = f'"{CONHOST_EXE}" "{LAUNCHER_BROWSER_TERMINAL}" "{app_id}"'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _key_path(name)) as handle:
        winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, "URL:" + name)
        winreg.SetValueEx(handle, "URL Protocol", 0, winreg.REG_SZ, "")
        winreg.SetValueEx(handle, LAUNCHER_MARKER, 0, winreg.REG_SZ, LAUNCHER_BROWSER_TERMINAL)
    if icon:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _key_path(name) + "\\DefaultIcon") as handle:
            winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, f'"{icon}",0')
    # The browser passes the whole link as an argument; it is not used, so no part of a link
    # (which any web page can contain) reaches the command line.
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _key_path(name) + "\\shell\\open\\command") as handle:
        winreg.SetValueEx(handle, "", 0, winreg.REG_SZ, command)
    return True


def unregister_start_link(name: str) -> bool:
    """Remove <name>:// if this launcher, or one in a folder that no longer exists, registered it."""
    import os
    import winreg

    owner = registered_launcher(name)
    if not owner:
        return False
    if os.path.normcase(owner) != os.path.normcase(LAUNCHER_BROWSER_TERMINAL) and Path(owner).exists():
        return False  # another existing copy of the program
    for sub_key in ("\\shell\\open\\command", "\\shell\\open", "\\shell", "\\DefaultIcon", ""):
        with contextlib.suppress(OSError):  # not there
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _key_path(name) + sub_key)
    return True

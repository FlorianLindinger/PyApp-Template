"""The launcher's side of the startup splash: when to show it, with which icon and message.

The window itself is scripts/standalone/splash.py, run as its own isolated process. The launcher's
stdin pipe owns its lifetime: EOF also closes it after a parent crash. Missing Tk never prevents
app startup.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Generator, List, Union

SPLASH_SCRIPT = Path(__file__).resolve().parents[1] / "standalone" / "splash.py"


def _message_for_this_start(settings: Union[ModuleType, SimpleNamespace], advance: bool) -> str:
    """The next line of splash_screen_messages; each start shows the next one (per PC, kept in
    generated/). The preview shows the one the next start will show, without moving on."""
    messages = [m for m in getattr(settings, "splash_screen_messages", ()) if isinstance(m, str) and m.strip()]
    if not messages:
        return ""
    from pyapp.DONT_CHANGE.pyapp_settings import SPLASH_MESSAGE_INDEX_PATH

    state = Path(SPLASH_MESSAGE_INDEX_PATH)
    try:
        index = int(state.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        index = 0
    if advance:
        with contextlib.suppress(OSError):
            state.write_text(str((index + 1) % len(messages)), encoding="utf-8")
    return messages[index % len(messages)]


def _icon_path() -> str:
    """The app icon for the splash, decided in about a millisecond: icon.png, unless its bytes are
    the shipped placeholder's, then the bundled default icon. (Notifications compare decoded
    pixels instead, which needs WPF and takes ~0.7 s; a re-saved placeholder is the only case
    where the two can differ.)"""
    import hashlib

    from pyapp.DONT_CHANGE.pyapp_settings import DEFAULT_ICON_DIR, ICON_PLACEHOLDER_SHA256, ICON_PNG_PATH

    default = str(Path(DEFAULT_ICON_DIR) / "default_icon.png")
    try:
        data = Path(ICON_PNG_PATH).read_bytes()
    except OSError:
        return default
    return default if hashlib.sha256(data).hexdigest() == ICON_PLACEHOLDER_SHA256 else ICON_PNG_PATH


def helper_command(
    settings: Union[ModuleType, SimpleNamespace], minimum_seconds: float = 0.5, preview: bool = False
) -> List[str]:
    """The splash process's command line; app starts and the preview tool share it, so the preview
    shows exactly what a start shows (name, icon, message, look)."""
    command = [
        sys.executable,
        "-I",
        "-S",
        str(SPLASH_SCRIPT),
        settings.program_name,
        _icon_path(),
        _message_for_this_start(settings, advance=not preview),
        str(minimum_seconds),
    ]
    return [*command, "preview"] if preview else command


@contextlib.contextmanager
def startup_splash(settings: Union[ModuleType, SimpleNamespace], mode: str = "") -> Generator[None, None, None]:
    """Show during startup; no-terminal minimum visibility runs independently of handoff."""
    child = None
    if (
        mode == "no_terminal"
        and getattr(settings, "show_splash_screen_for_no_terminal_start", False)
        and (not settings.start_minimized or settings.start_maximized)
    ):
        from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

        try:
            child = subprocess.Popen(  # noqa: S603 - fixed helper, separate literal arguments
                helper_command(settings),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception:
            note_ignored("start splash screen")
    try:
        yield
    finally:
        if child is not None:
            if child.stdin is not None:
                child.stdin.close()

            def reap() -> None:
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()

            threading.Thread(target=reap, daemon=True).start()

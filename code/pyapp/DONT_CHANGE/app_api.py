r"""pyapp_api: things main.py can use from the launcher. Import it with ``import pyapp_api``.

Only the standard library, Python 3.8+. Every function is safe to call when the app runs without
the launcher (``python main.py``): launcher features then do nothing and return a neutral value,
so the same code runs both ways. The dialogs need no launcher and always work on Windows.

What is available (details in each function's docstring):

    launched()                              True when started by the launcher (a shortcut)
    notify(title, message, open_path=None)  Windows notification under the app's name; a click opens open_path
    on_stop(callback)                       run callback() when the app is ended from outside
                                            (Stop shortcut, replacing start, Ctrl+C, the window's X)
    set_progress(fraction, state="normal")  progress on the taskbar button; None removes it
    set_overlay(icon_path, description="")  small badge (.ico) on the taskbar button; None removes it
    highlight(color="normal")               colour the whole taskbar button ("normal" green, "error" red,
                                            "paused" yellow); None removes it
    flash()                                 flash the taskbar button until the user switches to the app
    bring_to_front()                        show the app's window in front (Windows may only flash it)
    minimize_to_tray()                      hide the app's window into the tray (click the icon to restore);
                                            from then on minimizing it does the same
    set_title(text)                         the console window's title (also the browser terminal's tab)
    message_box(text, title=None, kind="info")  OK dialog ("info", "warning", "error")
    ask_yes_no(question, title=None)        Yes/No dialog; True for Yes
    keep_awake(display=False)               "with" block during which the PC does not sleep
    on_settings_changed(callback)           run callback() after the user saved code/settings.py
                                            ("import settings" then already shows the new values)
    report_error(error=None, note="")       crash log for a caught error; the app keeps running
    restart()                               end this run and start the app again the same way
    on_new_start(callback)                  receive the arguments of later starts (instance_policy
                                            "focus" or "prevent"), e.g. a file to open

Example:

    import pyapp_api

    pyapp_api.notify("Export finished", "12 files written", open_path=r"C:\out\report.txt")
    pyapp_api.on_stop(save_everything)          # runs when the app is ended from outside
    with pyapp_api.keep_awake():                # the PC does not go to sleep meanwhile
        for done in range(100):
            pyapp_api.set_progress(done / 100)  # progress on the taskbar button
    pyapp_api.set_progress(None)

The names in ``__all__`` are a stable contract (PROTECTED_APP_API_NAMES in backend_settings.py):
they are never removed or renamed within a major version. The machinery behind them is in
scripts/app_api_support.py.

How it gets there: runtime/script_wrapper.py registers this module as ``pyapp_api`` before it
runs main.py, and code/pyapp_api.py forwards to it when main.py runs without the launcher.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import traceback
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from pyapp.DONT_CHANGE.scripts import app_api_support as support

__all__ = [
    "ask_yes_no",
    "bring_to_front",
    "flash",
    "highlight",
    "keep_awake",
    "launched",
    "message_box",
    "minimize_to_tray",
    "notify",
    "on_new_start",
    "on_settings_changed",
    "on_stop",
    "report_error",
    "restart",
    "set_overlay",
    "set_progress",
    "set_title",
]


def launched() -> bool:
    """True when the app was started by the launcher (a shortcut), False for ``python main.py``."""
    return _launched


def notify(title: str, message: str = "", *, open_path: Optional[str] = None) -> bool:
    """Show a Windows notification under the app's name and icon.

    Clicking it opens ``open_path`` (a file or folder) with its default program, if given.
    Returns True when Windows accepted it. Needs the Start Menu shortcuts (start_menu_shortcuts),
    and Windows settings or Do not disturb can still hide it. Without the launcher: False.
    """
    if not _launched or os.name != "nt":
        return False
    try:
        from pyapp.DONT_CHANGE.scripts import windows_notifications

        app_id = os.environ.get("APP_ID", "")
        return windows_notifications.show(title, message, app_id, open_path=open_path) is None
    except Exception:
        return False


def on_stop(callback: Callable[[], None]) -> None:
    """Run ``callback()`` when the app is ended from outside: save data, release hardware.

    Covers the Stop shortcut and a replacing start (a console app gets a KeyboardInterrupt, a GUI a
    request to close its windows), Ctrl+C, and closing the window with X. The callbacks run once,
    in the order registered, after main.py has ended (for X: right away, on another thread).
    Keep them short: Stop ends the app by force after stop_timeout_seconds, and Windows ends a
    closed window's processes about five seconds after the X. A normal end runs nothing.
    """
    _stop_callbacks.append(callback)


def set_progress(fraction: Optional[float], state: str = "normal") -> bool:
    """Show progress on the app's taskbar button: ``fraction`` from 0.0 to 1.0, None to remove it.

    ``state``: "normal" (green), "paused" (yellow), "error" (red) or "indeterminate" (moving, no
    value). Works for the app's own window (Tkinter, Qt, ...) and the classic console; Windows
    Terminal shows its own indicator instead. Returns False when there is no window or no launcher.
    """
    if not _launched:
        return False
    if state not in support.PROGRESS_STATES or state == "none":
        raise ValueError('state must be "normal", "paused", "error" or "indeterminate"')

    def apply(taskbar: Any, interface: Any, hwnd: int) -> None:
        if fraction is None:
            interface.SetProgressState(taskbar, hwnd, support.PROGRESS_STATES["none"])
            return
        if state != "indeterminate":
            done = int(max(0.0, min(1.0, float(fraction))) * 1000)
            interface.SetProgressValue(taskbar, hwnd, done, 1000)
        interface.SetProgressState(taskbar, hwnd, support.PROGRESS_STATES[state])

    return support.with_taskbar(apply)


def set_overlay(icon_path: Optional[str], description: str = "") -> bool:
    """Show a small badge (an .ico file) on the app's taskbar button; None removes it.

    ``description`` is read out by screen readers. Same windows as set_progress.
    """
    if not _launched:
        return False

    def apply(taskbar: Any, interface: Any, hwnd: int) -> None:
        interface.SetOverlayIcon(taskbar, hwnd, support.load_icon(icon_path) if icon_path else 0, description)

    return support.with_taskbar(apply)


def highlight(color: Optional[str] = "normal") -> bool:
    """Colour the app's whole taskbar button: "normal" (green), "error" (red), "paused" (yellow).

    None removes the colour. A full progress bar is what Windows draws, so this replaces any
    set_progress value. Same windows as set_progress; without the launcher: False.
    """
    if color is None:
        return set_progress(None)
    if color not in ("normal", "error", "paused"):
        raise ValueError('color must be "normal", "error", "paused" or None')
    return set_progress(1.0, state=color)


def flash() -> bool:
    """Flash the app's taskbar button until the user switches to the app (without taking focus).

    Good for "your attention is needed" moments, e.g. a long job is done or a question waits.
    Without the launcher or a window: False.
    """
    hwnd = support.own_window() if _launched else 0
    if not hwnd:
        return False
    try:
        from pyapp.DONT_CHANGE.scripts.standalone.taskbar import flash as flash_window

        flash_window(hwnd)
        return True
    except Exception:
        return False


def bring_to_front() -> bool:
    """Restore the app's window if minimized and bring it to the front.

    Windows lets a program take the focus only in certain situations (e.g. right after the user
    clicked it); otherwise it flashes the taskbar button instead. True when the window is in front.
    """
    hwnd = support.own_window() if _launched else 0
    if not hwnd:
        return False
    try:
        from pyapp.DONT_CHANGE.scripts.windows_focus import focus_window

        return bool(focus_window(hwnd))
    except Exception:
        return False


def minimize_to_tray() -> bool:
    """Hide the app's window into the system tray (beside the clock); clicking its icon restores it.

    From then on, minimizing the window also moves it to the tray. Right-click on the icon offers
    Restore and Stop (Stop closes the window as its X would). Works for the app's own window and the
    classic console. Without the launcher or a window: False.
    """
    hwnd = support.own_window() if _launched else 0
    if not hwnd:
        return False
    try:
        import ctypes

        from pyapp.DONT_CHANGE import backend_settings as paths

        support.tray_controller(hwnd, support.program_name(), paths.ICON_PATH)
        ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE: the controller then moves it to the tray
        return True
    except Exception:
        return False


def set_title(text: str) -> bool:
    """Set the title of the app's console window, or of the browser terminal's tab.

    For your own GUI window, set its title with the GUI toolkit (Tkinter: root.title(...)). Useful
    for progress in a console app, e.g. set_title("Processing 3 of 10"). Without the launcher: False.
    """
    if not _launched:
        return False
    from pyapp.DONT_CHANGE.scripts.console_tools import set_terminal_title

    set_terminal_title(str(text))
    return True


def message_box(text: str, title: Optional[str] = None, *, kind: str = "info") -> None:
    """A Windows message box with an OK button; useful for apps without a terminal or GUI.

    ``kind``: "info", "warning" or "error" (the icon). Works with and without the launcher;
    elsewhere than Windows it prints the text instead.
    """
    icons = {"info": 0x40, "warning": 0x30, "error": 0x10}
    if kind not in icons:
        raise ValueError('kind must be "info", "warning" or "error"')
    if os.name != "nt":
        print(f"{title or support.program_name()}: {text}")
        return
    import ctypes

    ctypes.windll.user32.MessageBoxW(None, str(text), title or support.program_name(), icons[kind] | 0x10000)


def ask_yes_no(question: str, title: Optional[str] = None) -> bool:
    """A Windows Yes/No question; True for Yes. Works with and without the launcher.

    Elsewhere than Windows it asks in the terminal.
    """
    if os.name != "nt":
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    import ctypes

    answer = ctypes.windll.user32.MessageBoxW(
        None, str(question), title or support.program_name(), 0x04 | 0x20 | 0x10000
    )
    return answer == 6  # IDYES


@contextlib.contextmanager
def keep_awake(display: bool = False) -> Iterator[None]:
    """While the ``with`` block runs, the PC does not go to sleep (``display=True``: nor the screen).

    Windows ends the request when the block ends or the app ends. Without the launcher: no effect.
    """
    if not _launched or os.name != "nt":
        yield
        return
    from pyapp.DONT_CHANGE.scripts.standalone.power import set_awake

    set_awake(True, display)
    try:
        yield
    finally:
        set_awake(False, False)


def on_settings_changed(callback: Callable[[], None]) -> bool:
    """Run ``callback()`` (on a background thread) after the user saved the app's settings file.

    The file is code/settings.py, or user_settings_path in developer_settings.py. If main.py did
    "import settings", that module is reloaded first, so ``settings.x`` already has the new value. A
    file saved with a mistake prints the error and skips the callback. A GUI should hand the work to
    its own thread (Tkinter: root.after, Qt: a signal). Without the launcher or a settings file: False.
    """
    path = os.environ.get("USER_SETTINGS_PATH", "") if _launched else ""
    if not path:
        return False
    from pathlib import Path

    def changed() -> None:
        try:
            support.reload_settings_module(Path(path))
        except Exception:
            traceback.print_exc()  # e.g. a syntax error while the file is being edited
            return
        callback()

    support.watch_file(Path(path), changed)
    return True


def report_error(error: Optional[BaseException] = None, note: str = "") -> Optional[str]:
    """Write a crash log for an error the app caught, and keep running; returns the file's path.

    Call it in an ``except`` block (``error`` defaults to the error being handled). The crash log
    looks like the launcher's own, with source lines and values, and lands in the crash log folder.
    Without the launcher (or with crash logs turned off): None, nothing is written.
    """
    if not _launched:
        return None
    if error is None:
        error = sys.exc_info()[1]
        if error is None:
            raise ValueError("report_error() needs an error, or must be called in an except block")
    try:
        from pyapp.DONT_CHANGE.runtime import _pyapp as protocol
        from pyapp.DONT_CHANGE.runtime import process_exit

        report_file = support.FORWARD_DIR.parent / f"handled-{uuid.uuid4().hex[:12]}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            protocol.save_report(
                error,
                str(_launch.get("script") or sys.argv[0]),
                str(report_file),
                _launch.get("app_root"),
                _context_lines(),
            )
            report = json.loads(report_file.read_text(encoding="utf-8"))
        finally:
            with contextlib.suppress(OSError):
                report_file.unlink()
        message = "Handled error (the app kept running)" + (f": {note}" if note else "")
        path = process_exit.write_crash_log(report, message, os.environ.get("LOG_PATH") or None)
        if path:
            print(f"Crash log written: {path}", file=sys.stderr)
        return path
    except Exception:
        return None


def restart() -> None:
    """End this run and start the app again the same way (same shortcut, same kind of window).

    Raises SystemExit(0), so call it from the main thread; the new start follows once this run has
    ended. Without the launcher: does nothing and returns.
    """
    if not _launched or os.name != "nt":
        return
    support.start_after_exit(str(_launch.get("launch_mode", "")), str(_launch.get("app_id", "")))
    raise SystemExit(0)


def on_new_start(callback: Callable[[List[str], str], None]) -> bool:
    """Receive later starts of the app while it runs: ``callback(arguments, start_folder)``.

    With instance_policy = "focus" or "prevent", starting the app again (a shortcut, a batch entry
    point, a file opened with it) does not start a second copy: its arguments are passed to this
    one instead, e.g. a file to open. The callback runs on a background thread; a GUI should hand
    the work to its own thread (Tkinter: root.after, Qt: a signal). Without the launcher: False.
    """
    if not _launched:
        return False
    support.listen_for_starts(callback)
    return True


# ------------------------------------------------------------------ internal (used by the launcher)

# Set by runtime/script_wrapper.py before main.py runs; stays False/empty for ``python main.py``.
_launched = False
_launch: Dict[str, Any] = {}
_stop_callbacks: List[Callable[[], None]] = []


def _context_lines() -> Tuple[int, int]:
    """Source lines shown before and after the failing line in a crash report (from the launcher)."""
    before, after = [*list(_launch.get("context_lines") or []), 3, 3][:2]
    return int(before), int(after)


def _run_stop_callbacks() -> None:
    """Called by the wrapper when the app was ended from outside; one failing callback does not skip the rest."""
    while _stop_callbacks:
        callback = _stop_callbacks.pop(0)
        try:
            callback()
        except Exception:
            traceback.print_exc()

"""Native terminal taskbar progress and attention, without taking keyboard focus.

Which window and when, from the settings; the taskbar calls themselves (ITaskbarList3 progress,
FlashWindowEx) are in standalone/taskbar.py. The stored window owner is checked before a
completion subprocess reuses its handle.
"""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from types import ModuleType, SimpleNamespace
from typing import Union

from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
from pyapp.DONT_CHANGE.scripts.standalone.taskbar import (
    TBPF_ERROR,
    TBPF_INDETERMINATE,
    TBPF_NOPROGRESS,
    TBPF_NORMAL,
    flash,
    set_progress,
)

WINDOW_ENV = "PYAPP_TERMINAL_WINDOW"
ACTIVITY_ENV = "PYAPP_TASKBAR_ACTIVITY"


def remember_window(hwnd: int) -> None:
    """Pass this native terminal's handle and owner to the completion subprocess."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    os.environ[WINDOW_ENV] = json.dumps({"hwnd": hwnd, "pid": pid.value})


def terminal_window(*, include_hidden: bool = False) -> int:
    """A still-valid native terminal; completion may update a remembered hidden window's state."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.IsWindow.argtypes = [wintypes.HWND]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    if WINDOW_ENV in os.environ:
        try:
            record = json.loads(os.environ[WINDOW_ENV])
            hwnd, owner = record["hwnd"], record["pid"]
            if not isinstance(hwnd, int) or not isinstance(owner, int) or not user.IsWindow(hwnd):
                return 0
        except (ValueError, KeyError, TypeError):
            return 0
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != owner:
            return 0
    else:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetConsoleWindow.restype = wintypes.HWND
        hwnd = kernel.GetConsoleWindow()
    if not hwnd or (not user.IsWindowVisible(hwnd) and not (include_hidden and WINDOW_ENV in os.environ)):
        return 0
    name = ctypes.create_unicode_buffer(256)
    user.GetClassNameW(hwnd, name, len(name))
    return hwnd if name.value in ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS") else 0


def start(s: Union[ModuleType, SimpleNamespace]) -> None:
    """Best-effort running activity, after the terminal's title/taskbar identity have been set."""
    if not getattr(s, "have_running_animation_in_taskbar", False):
        return
    try:
        hwnd = terminal_window()
        if hwnd:
            set_progress(hwnd, TBPF_INDETERMINATE)
            os.environ[ACTIVITY_ENV] = "1"
    except Exception:
        note_ignored("taskbar running animation")


def finish(s: Union[ModuleType, SimpleNamespace], outcome: str, stays_open: bool) -> None:
    """Replace activity with an optional completion highlight/flash; Ctrl+C only clears activity."""
    highlight = outcome in ("success", "failure") and getattr(s, "highlight_on_" + outcome, False)
    flashing = outcome in ("success", "failure") and getattr(s, "flash_on_" + outcome, False)
    if not (
        getattr(s, "have_running_animation_in_taskbar", False) or os.environ.get(ACTIVITY_ENV) or highlight or flashing
    ):
        return
    try:
        hwnd = terminal_window(include_hidden=True)
        if not hwnd:
            return
    except Exception:
        note_ignored("find completion taskbar window")
        return
    try:
        state = (TBPF_NORMAL if outcome == "success" else TBPF_ERROR) if stays_open and highlight else TBPF_NOPROGRESS
        set_progress(hwnd, state)
        os.environ.pop(ACTIVITY_ENV, None)
    except Exception:
        note_ignored("taskbar completion progress")
    # Flashing remains independent if the shell rejects a progress update.
    if stays_open and flashing:
        try:
            flash(hwnd)
        except Exception:
            note_ignored("taskbar completion flashing")

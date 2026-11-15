"""Native terminal controls for windows owned by conhost/WT rather than the Python process.

CTRL_CLOSE_EVENT permits cleanup but always terminates the process, even if its handler returns
True (https://learn.microsoft.com/en-us/windows/console/handlerroutine). Prompt/hide therefore
require host-owned close handling; do not advertise a console control handler as cancellation.
"""

from __future__ import annotations

import ctypes
import secrets
import time
from ctypes import wintypes
from types import ModuleType, SimpleNamespace
from typing import List, Union

from pyapp.DONT_CHANGE.scripts.errors import SettingsError

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_EX_LAYERED = 0x00080000
SC_CLOSE = 0xF060
SC_MINIMIZE = 0xF020
SC_MAXIMIZE = 0xF030
MF_GRAYED = 0x00000001
LWA_ALPHA = 0x00000002
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


def validate_close_mode(s: Union[ModuleType, SimpleNamespace], mode: str) -> None:
    """Reject unavailable policies before creating an app or doing environment work."""
    supported = {
        "conhost": ("close", "block"),
        "wt": ("close",),
        "browser": ("close", "prompt", "hide"),
    }
    if mode in supported and s.confirm_on_close not in supported[mode]:
        reason = (
            "Browsers cannot unconditionally block tab closing; use 'prompt' to request confirmation."
            if mode == "browser"
            else "Native console close notifications cannot cancel termination."
        )
        raise SettingsError(
            f"confirm_on_close = {s.confirm_on_close!r} is unsupported for {mode}; "
            + "use "
            + ", ".join(repr(value) for value in supported[mode])
            + ". "
            + reason
        )


def needs_window(s: Union[ModuleType, SimpleNamespace]) -> bool:
    """Whether WT needs a dedicated window to avoid changing unrelated tabs."""
    return (
        s.terminal_alpha is not None
        or s.always_on_top
        or getattr(s, "start_maximized", False)
        or any(
            getattr(s, name, False)
            for name in (
                "replace_minimize_with_minimize_to_system_tray",
                "have_running_animation_in_taskbar",
                "highlight_on_success",
                "highlight_on_failure",
                "flash_on_success",
                "flash_on_failure",
            )
        )
    )


def _terminal_hwnd(marker: str, timeout: float = 5.0) -> int:
    """Find only the WT window showing this run's unpredictable temporary console title."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    found: List[int] = []

    def visit(hwnd: int, _data: int) -> bool:
        title = ctypes.create_unicode_buffer(1024)
        name = ctypes.create_unicode_buffer(256)
        user.GetClassNameW(hwnd, name, len(name))
        if name.value == "CASCADIA_HOSTING_WINDOW_CLASS" and user.IsWindowVisible(hwnd):
            user.GetWindowTextW(hwnd, title, len(title))
            if marker in title.value:
                found.append(hwnd)
                return False
        return True

    callback = callback_type(visit)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        user.EnumWindows(callback, 0)
        if found:
            return found[0]
        time.sleep(0.05)
    raise RuntimeError("Could not identify this run's Windows Terminal window; window options were not applied.")


def apply_window_settings(hwnd: int, s: Union[ModuleType, SimpleNamespace], classic: bool) -> None:
    """Apply native styles with pointer-safe handles, without activating or moving the window."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user.GetWindowLongW.restype = wintypes.LONG
    user.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user.SetWindowLongW.restype = wintypes.LONG
    user.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
    user.GetSystemMenu.restype = wintypes.HMENU
    user.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user.EnableMenuItem.restype = wintypes.UINT
    user.DrawMenuBar.argtypes = [wintypes.HWND]
    user.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD]

    def set_style(index: int, value: int) -> None:
        ctypes.set_last_error(0)
        if not user.SetWindowLongW(hwnd, index, value) and ctypes.get_last_error():
            raise ctypes.WinError(ctypes.get_last_error())

    if s.terminal_alpha is not None:
        extended = user.GetWindowLongW(hwnd, GWL_EXSTYLE)
        set_style(GWL_EXSTYLE, extended | WS_EX_LAYERED)
        if not user.SetLayeredWindowAttributes(hwnd, 0, max(1, round(s.terminal_alpha * 255)), LWA_ALPHA):
            raise ctypes.WinError(ctypes.get_last_error())
    allow_minimize = getattr(s, "allow_minimize", True)
    allow_maximize = getattr(s, "allow_maximize", True)
    if classic and (s.hide_minimize_button or s.hide_maximize_button or not allow_minimize or not allow_maximize):
        style = user.GetWindowLongW(hwnd, GWL_STYLE)
        if s.hide_minimize_button or not allow_minimize:
            style &= ~WS_MINIMIZEBOX
        if s.hide_maximize_button or not allow_maximize:
            style &= ~WS_MAXIMIZEBOX
        set_style(GWL_STYLE, style)
    if classic and s.confirm_on_close == "block":
        menu = user.GetSystemMenu(hwnd, False)
        if not menu or user.EnableMenuItem(menu, SC_CLOSE, MF_GRAYED) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        user.DrawMenuBar(hwnd)
    if classic and (not allow_minimize or not allow_maximize):
        menu = user.GetSystemMenu(hwnd, False)
        if not menu:
            raise ctypes.WinError(ctypes.get_last_error())
        for command, allowed in ((SC_MINIMIZE, allow_minimize), (SC_MAXIMIZE, allow_maximize)):
            if not allowed and user.EnableMenuItem(menu, command, MF_GRAYED) == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
        user.DrawMenuBar(hwnd)
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED
    if not s.always_on_top:
        flags |= SWP_NOZORDER
    if not user.SetWindowPos(hwnd, HWND_TOPMOST if s.always_on_top else 0, 0, 0, 0, 0, flags):
        raise ctypes.WinError(ctypes.get_last_error())


def configure(s: Union[ModuleType, SimpleNamespace], mode: str) -> None:
    """Apply settings inside the watchdog before the app can print or change its title."""
    if mode not in ("conhost", "wt"):
        return
    if mode == "wt" and not needs_window(s):
        return
    if mode == "conhost" and not (
        needs_window(s)
        or s.hide_minimize_button
        or s.hide_maximize_button
        or s.confirm_on_close == "block"
        or not getattr(s, "allow_minimize", True)
        or not getattr(s, "allow_maximize", True)
    ):
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetConsoleWindow.restype = wintypes.HWND
    kernel.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
    if mode == "wt":
        marker = "PyApp-window-" + secrets.token_hex(16)
        if not kernel.SetConsoleTitleW(marker):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            hwnd = _terminal_hwnd(marker)
        finally:
            kernel.SetConsoleTitleW(s.program_name)
    else:
        hwnd = kernel.GetConsoleWindow()
    if not hwnd:
        raise RuntimeError("The native terminal has no window to configure.")
    apply_window_settings(hwnd, s, classic=mode == "conhost")
    from pyapp.DONT_CHANGE.scripts.taskbar_status import remember_window

    remember_window(hwnd)
    if getattr(s, "start_maximized", False):
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user.ShowWindow(hwnd, 3)  # SW_MAXIMIZE; host-owned window, never an application's GUI.


def enable_close(hwnd: int) -> None:
    """Restore conhost's Close command after the application has ended."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
    user.GetSystemMenu.restype = wintypes.HMENU
    user.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user.EnableMenuItem.restype = wintypes.UINT
    user.DrawMenuBar.argtypes = [wintypes.HWND]
    menu = user.GetSystemMenu(hwnd, False)
    if not menu or user.EnableMenuItem(menu, SC_CLOSE, 0) == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    user.DrawMenuBar(hwnd)

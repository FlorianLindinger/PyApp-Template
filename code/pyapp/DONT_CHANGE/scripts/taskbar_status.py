"""Native terminal taskbar progress and attention, without taking keyboard focus.

ITaskbarList3 owns progress colours/animation; FlashWindowEx requests Windows' attention flash.
The stored window owner is checked before a completion subprocess reuses its handle.
"""

from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from types import ModuleType, SimpleNamespace
from typing import Union

from pyapp.DONT_CHANGE.scripts import com_tools as com
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

WINDOW_ENV = "PYAPP_TERMINAL_WINDOW"
ACTIVITY_ENV = "PYAPP_TASKBAR_ACTIVITY"
TBPF_NOPROGRESS = 0
TBPF_INDETERMINATE = 1
TBPF_NORMAL = 2
TBPF_ERROR = 4
FLASHW_TRAY = 2
FLASHW_TIMERNOFG = 12


class _Taskbar(ctypes.Structure):
    pass


TaskbarPointer = ctypes.POINTER(_Taskbar)


class _TaskbarVTable(ctypes.Structure):
    # Only the prefix through SetProgressState is called; later methods need no declarations.
    _fields_ = (
        ("QueryInterface", com.UNUSED_METHOD),
        ("AddRef", com.UNUSED_METHOD),
        ("Release", com.METHOD(ctypes.c_ulong, TaskbarPointer)),
        ("HrInit", com.METHOD(com.HRESULT, TaskbarPointer)),
        ("AddTab", com.UNUSED_METHOD),
        ("DeleteTab", com.UNUSED_METHOD),
        ("ActivateTab", com.UNUSED_METHOD),
        ("SetActiveAlt", com.UNUSED_METHOD),
        ("MarkFullscreenWindow", com.UNUSED_METHOD),
        (
            "SetProgressValue",
            com.METHOD(com.HRESULT, TaskbarPointer, wintypes.HWND, ctypes.c_ulonglong, ctypes.c_ulonglong),
        ),
        ("SetProgressState", com.METHOD(com.HRESULT, TaskbarPointer, wintypes.HWND, ctypes.c_int)),
    )


_Taskbar._fields_ = [("vtable", ctypes.POINTER(_TaskbarVTable))]


class FLASHWINFO(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("dwFlags", wintypes.DWORD),
        ("uCount", wintypes.UINT),
        ("dwTimeout", wintypes.DWORD),
    )


def remember_window(hwnd: int) -> None:
    """Pass this native terminal's handle and owner to the completion subprocess."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    os.environ[WINDOW_ENV] = json.dumps({"hwnd": hwnd, "pid": pid.value})


def terminal_window() -> int:
    """A still-valid remembered terminal, or this process's visible classic console; never a browser."""
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
    if not hwnd or not user.IsWindowVisible(hwnd):
        return 0
    name = ctypes.create_unicode_buffer(256)
    user.GetClassNameW(hwnd, name, len(name))
    return hwnd if name.value in ("ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS") else 0


def set_progress(hwnd: int, state: int) -> None:
    """Set activity, steady full success/failure colour, or clear the taskbar progress indicator."""
    ole = ctypes.WinDLL("ole32", use_last_error=True)
    ole.CoCreateInstance.argtypes = [
        ctypes.POINTER(com.GUID),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(com.GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    ole.CoCreateInstance.restype = com.HRESULT
    clsid = com.guid("56FDF344-FD6D-11D0-958A-006097C9A090")
    iid = com.guid("EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF")
    initialized = com.co_initialize()
    try:
        raw = ctypes.c_void_p()
        com.check_hresult(
            ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(raw)),
            "CoCreateInstance(ITaskbarList3)",
        )
        taskbar = ctypes.cast(raw, TaskbarPointer)
        interface = taskbar.contents.vtable.contents
        try:
            com.check_hresult(interface.HrInit(taskbar), "ITaskbarList3.HrInit")
            if state in (TBPF_NORMAL, TBPF_ERROR):
                # SetProgressValue can switch away from indeterminate/error, so set the colour last.
                com.check_hresult(interface.SetProgressValue(taskbar, hwnd, 1, 1), "SetProgressValue")
            com.check_hresult(interface.SetProgressState(taskbar, hwnd, state), "SetProgressState")
        finally:
            interface.Release(taskbar)
    finally:
        com.co_uninitialize(initialized)


def flash(hwnd: int) -> None:
    """Flash the taskbar until foreground activation; Windows controls the cadence."""
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.FlashWindowEx.argtypes = [ctypes.POINTER(FLASHWINFO)]
    info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, FLASHW_TRAY | FLASHW_TIMERNOFG, 0, 0)
    # Its return value is the previous active state, not an error/success indicator.
    user.FlashWindowEx(ctypes.byref(info))


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
        hwnd = terminal_window()
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

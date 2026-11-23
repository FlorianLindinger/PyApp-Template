"""Taskbar progress states and attention flashing for any window, without taking keyboard focus.

Standalone: copy this file anywhere, together with com_tools.py (needs com_tools.py next to it,
in one package folder). Standard library only (ctypes); Windows only.

set_progress(hwnd, state): ITaskbarList3 progress (TBPF_INDETERMINATE: running animation;
TBPF_NORMAL / TBPF_ERROR: a full green / red bar; TBPF_NOPROGRESS: clear).
flash(hwnd): FlashWindowEx, until the window comes to the foreground.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from . import com_tools as com

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

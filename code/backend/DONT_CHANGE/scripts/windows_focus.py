"""Bring a running app instance's window to the front (instance_policy = "focus")."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any, Dict, Iterable, List, Optional, Set

TH32CS_SNAPPROCESS = 0x00000002
SW_RESTORE = 9
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
ASFW_ANY = -1


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def process_tree(root_pids: Iterable[Optional[int]]) -> Set[int]:
    """The given processes and all their descendants."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)]
    snapshot = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    children = {}
    try:
        entry = _ProcessEntry()
        entry.dwSize = ctypes.sizeof(_ProcessEntry)
        ok = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            children.setdefault(entry.th32ParentProcessID, []).append(entry.th32ProcessID)
            ok = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    result = set()
    pending = [pid for pid in root_pids if pid]
    while pending:
        pid = pending.pop()
        if pid in result:
            continue
        result.add(pid)
        pending.extend(children.get(pid, []))
    return result


def app_windows(pids: Set[int]) -> List[int]:
    """Visible top-level application windows (not consoles) owned by these processes."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _: int):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, GW_OWNER):
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, name, 256)
            if name.value not in ("ConsoleWindowClass", "PseudoConsoleWindow"):
                found.append(hwnd)
        return True

    user32.EnumWindows(callback_type(callback), 0)
    return found


def focus_window(hwnd: int) -> bool:
    """Restore and activate a window; Windows may only flash its taskbar button."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.AllowSetForegroundWindow(ASFW_ANY)
    if user32.SetForegroundWindow(hwnd):
        return True
    # A short Alt key press lifts the foreground lock for this process.
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    if user32.SetForegroundWindow(hwnd):
        return True
    user32.FlashWindow(hwnd, True)
    return True


def focus_instance(record: Dict[str, Any]) -> str:
    """Return "focused", or "no_window" when the instance has neither app nor console window."""
    child = (record.get("child") or {}).get("pid") if isinstance(record.get("child"), dict) else None
    windows = app_windows(process_tree([record.get("pid"), child]))
    if windows and focus_window(windows[0]):
        return "focused"
    console = record.get("console_hwnd") or 0
    if console and focus_window(console):
        return "focused"
    return "no_window"

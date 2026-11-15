"""Keep a native terminal recoverable in the Windows notification area when it is minimized.

The terminal belongs to conhost/WT, so its window procedure cannot be subclassed from Python.
A small message loop observes only its minimized state. The tray icon must exist before hiding
the terminal, and cleanup restores hidden windows so a failed controller cannot strand them.
"""

from __future__ import annotations

import ctypes
import threading
import uuid
from ctypes import wintypes
from typing import Callable, Optional

from pyapp.DONT_CHANGE.scripts.com_tools import GUID
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

METHOD = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
WNDPROC = METHOD(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_TIMER = 0x0113
WM_TRAY = 0x8001
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIM_SETVERSION = 4
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
NIF_INFO = 0x10
NIF_SHOWTIP = 0x80
SW_HIDE = 0
SW_RESTORE = 9
SW_SHOWMINNOACTIVE = 7


def _short_text(text: str, units: int) -> str:
    """Fit a WCHAR array without cutting an emoji's UTF-16 surrogate pair."""
    return text.encode("utf-16-le", errors="replace")[: units * 2].decode("utf-16-le", errors="ignore")


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", GUID),
        ("hBalloonIcon", wintypes.HICON),
    )


class WNDCLASS(ctypes.Structure):
    _fields_ = (
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    )


class MinimizeToTray:
    """One tray controller, owned by the watchdog for the entire run including completion prompts."""

    def __init__(self, target: int, name: str, icon_path: str, on_stop: Callable[[], None]) -> None:
        self.target = target
        self.name = name
        self.icon_path = icon_path
        self.on_stop = on_stop
        self.hwnd = 0
        self.icon = 0
        self.owns_icon = False
        self.added = False
        self.hidden = False
        self.ready = threading.Event()
        self.closing = threading.Event()
        self.activate_on_close = True
        self.error: Optional[Exception] = None
        self.thread = threading.Thread(target=self._run, name="PyApp system tray", daemon=True)
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.shell = ctypes.WinDLL("shell32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_api()
        self.owner_pid = self._owner()

    def _configure_api(self) -> None:
        user = self.user
        user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user.IsWindow.argtypes = [wintypes.HWND]
        user.IsIconic.argtypes = [wintypes.HWND]
        user.IsWindowVisible.argtypes = [wintypes.HWND]
        user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        user.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
        user.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        user.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            ctypes.c_void_p,
        ]
        user.CreateWindowExW.restype = wintypes.HWND
        user.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.DefWindowProcW.restype = ctypes.c_ssize_t
        user.DestroyWindow.argtypes = [wintypes.HWND]
        user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user.DispatchMessageW.restype = ctypes.c_ssize_t
        user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
        user.SetTimer.restype = ctypes.c_size_t
        user.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
        user.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        user.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user.LoadImageW.restype = wintypes.HANDLE
        user.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        user.LoadIconW.restype = wintypes.HICON
        user.DestroyIcon.argtypes = [wintypes.HICON]
        user.CreatePopupMenu.restype = wintypes.HMENU
        user.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
        user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user.TrackPopupMenu.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            ctypes.c_void_p,
        ]
        user.DestroyMenu.argtypes = [wintypes.HMENU]
        self.kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel.GetModuleHandleW.restype = wintypes.HMODULE
        self.shell.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]

    def _owner(self) -> int:
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(self.target, ctypes.byref(pid))
        return pid.value

    def _valid(self) -> bool:
        return bool(self.user.IsWindow(self.target) and self.owner_pid and self._owner() == self.owner_pid)

    def _data(self, flags: int) -> NOTIFYICONDATA:
        data = NOTIFYICONDATA()
        data.cbSize = ctypes.sizeof(data)
        data.hWnd = self.hwnd
        data.uID = 1
        data.uFlags = flags
        data.uCallbackMessage = WM_TRAY
        data.hIcon = self.icon
        data.szTip = _short_text(self.name + " - click to restore; right-click for menu", 127)
        return data

    def _add_icon(self) -> None:
        data = self._data(NIF_MESSAGE | NIF_ICON | NIF_TIP | NIF_SHOWTIP)
        if not self.shell.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data)):
            raise OSError("Windows could not create the system tray icon; the terminal will stay accessible.")
        self.added = True
        data.uVersion = 4
        if not self.shell.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(data)):
            raise OSError("Windows could not enable tray interaction version 4.")

    def minimize(self) -> None:
        """Hide only after the icon is available, requesting an explanatory notification every time."""
        if self.hidden or not self._valid():
            return
        if not self.added:
            self._add_icon()
        self.user.ShowWindow(self.target, SW_HIDE)
        self.hidden = True
        data = self._data(NIF_INFO)
        data.szInfoTitle = _short_text(self.name + " is in the system tray", 63)
        data.szInfo = (
            "The window moved to the system tray beside the clock (possibly under the hidden-icons arrow). "
            "Minimizing does not stop the program. Click its icon or this notification to restore it. "
            "Right-click for Restore / Stop."
        )
        data.dwInfoFlags = 1 | 0x10  # NIIF_INFO | NIIF_NOSOUND; completion sound settings stay independent.
        if not self.shell.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data)):
            self.restore()
            note_ignored("send minimize-to-tray notification")

    def restore(self) -> None:
        """Show the terminal and remove its tray entry; the next minimize recreates it."""
        if self._valid():
            # Duplicate Shell callbacks must not unmaximize an already-restored window.
            if self.user.IsIconic(self.target) or not self.user.IsWindowVisible(self.target):
                self.user.ShowWindow(self.target, SW_RESTORE)
            self.user.SetForegroundWindow(self.target)
        self.hidden = False
        self._remove_icon()

    def _remove_icon(self) -> None:
        if self.added:
            if self.shell.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._data(0))):
                self.added = False
            else:
                # Keep tracking it so the timer/cleanup can retry a failed Shell deletion.
                note_ignored("remove restored window's system tray icon")

    def _tick(self) -> None:
        if self.closing.is_set() or not self._valid():
            self.user.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        elif self.hidden and self.user.IsWindowVisible(self.target):
            # Instance-policy focus and completion foreground requests can also restore it.
            self.hidden = False
            self._remove_icon()
        elif not self.hidden and self.user.IsIconic(self.target):
            self.minimize()
        elif not self.hidden and self.added:
            self._remove_icon()

    def _menu(self) -> None:
        menu = self.user.CreatePopupMenu()
        if not menu:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            self.user.AppendMenuW(menu, 0, 1, "Restore")
            self.user.AppendMenuW(menu, 0, 2, "Stop program")
            point = wintypes.POINT()
            self.user.GetCursorPos(ctypes.byref(point))
            self.user.SetForegroundWindow(self.hwnd)
            choice = self.user.TrackPopupMenu(menu, 0x100 | 2, point.x, point.y, 0, self.hwnd, None)
            self.user.PostMessageW(self.hwnd, 0, 0, 0)
            if choice == 1:
                self.restore()
            elif choice == 2:
                self.restore()
                self.on_stop()
        finally:
            self.user.DestroyMenu(menu)

    def _message(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        try:
            if message == self.restart_message:
                # Explorer forgot the icon. Restore first; never leave a window hidden without recovery.
                self.added = False
                if self.hidden:
                    self.restore()
                return 0
            if message == WM_TIMER:
                self._tick()
                return 0
            if message == WM_TRAY:
                event = lparam & 0xFFFF  # NOTIFYICON_VERSION_4 packs the icon ID into the high word.
                if event in (0x400, 0x401, 0x405, 0x202, 0x203):
                    self.restore()
                elif event in (0x7B, 0x205):
                    self._menu()
                return 0
            if message == WM_CLOSE:
                self.user.DestroyWindow(hwnd)
                return 0
            if message == WM_DESTROY:
                self.user.PostQuitMessage(0)
                return 0
        except Exception:
            note_ignored("system tray event")
            self.restore()
        return self.user.DefWindowProcW(hwnd, message, wparam, lparam)

    def _run(self) -> None:
        instance = self.kernel.GetModuleHandleW(None)
        name = "PyAppTray_" + uuid.uuid4().hex
        registered = False
        # Keep the callback alive for every native call, including DestroyWindow's final messages.
        callback = WNDPROC(self._message)
        try:
            self.restart_message = self.user.RegisterWindowMessageW("TaskbarCreated")
            if not self.restart_message:
                raise ctypes.WinError(ctypes.get_last_error())
            window_class = WNDCLASS()
            window_class.lpfnWndProc = callback
            window_class.hInstance = instance
            window_class.lpszClassName = name
            if not self.user.RegisterClassW(ctypes.byref(window_class)):
                raise ctypes.WinError(ctypes.get_last_error())
            registered = True
            self.hwnd = self.user.CreateWindowExW(0, name, "", 0, 0, 0, 0, 0, None, None, instance, None)
            if not self.hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            self.icon = self.user.LoadImageW(None, self.icon_path, 1, 16, 16, 0x10)
            self.owns_icon = bool(self.icon)
            if not self.icon:
                self.icon = self.user.LoadIconW(None, ctypes.c_void_p(32512))  # shared application icon
            if not self.icon:
                raise ctypes.WinError(ctypes.get_last_error())
            if self.closing.is_set():
                raise RuntimeError("The tray controller was closed during startup.")
            if not self.user.SetTimer(self.hwnd, 1, 100, None):
                raise ctypes.WinError(ctypes.get_last_error())
            self.ready.set()
            message = wintypes.MSG()
            while True:
                result = self.user.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == 0:
                    break
                self.user.TranslateMessage(ctypes.byref(message))
                self.user.DispatchMessageW(ctypes.byref(message))
        except Exception as error:
            self.error = error
            note_ignored("system tray controller")
        finally:
            if self.hidden:
                if self.activate_on_close:
                    self.restore()
                else:
                    # Normal watchdog exit must not steal focus or flash the terminal open.
                    # A surviving console (e.g. a child still attached) remains recoverable.
                    if self._valid():
                        self.user.ShowWindow(self.target, SW_SHOWMINNOACTIVE)
                    self.hidden = False
            self._remove_icon()
            if self.hwnd and self.user.IsWindow(self.hwnd):
                self.user.KillTimer(self.hwnd, 1)
                self.user.DestroyWindow(self.hwnd)
            if self.owns_icon:
                self.user.DestroyIcon(self.icon)
            if registered:
                self.user.UnregisterClassW(name, instance)
            self.hwnd = 0
            self.ready.set()

    def start(self) -> None:
        self.thread.start()
        if not self.ready.wait(5):
            self.close()
            raise TimeoutError("The system tray controller did not start; the terminal was not hidden.")
        if self.error:
            raise self.error

    def close(self, *, activate: bool = True) -> None:
        """Remove the icon; normal watchdog shutdown returns hidden windows to the taskbar quietly."""
        self.activate_on_close = activate
        self.closing.set()
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
        if self.thread.is_alive() and self.thread is not threading.current_thread():
            self.thread.join(timeout=5)

"""The machinery behind app_api.py ("import pyapp_api"): windows, the taskbar, restarts, forwarded starts.

Not part of the public contract: app_api.py is what apps use, and only its names are protected.
Standard library only, Python 3.8+, because it runs in the app's own Python.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable, List

DONT_CHANGE = Path(__file__).resolve().parents[1]
# Forwarded starts: a listener file per running app, and one small JSON file per forwarded start.
FORWARD_DIR = DONT_CHANGE / "tmp" / "forwarded"
# Taskbar progress states of ITaskbarList3 (TBPF_*).
PROGRESS_STATES = {"none": 0, "indeterminate": 1, "normal": 2, "error": 4, "paused": 8}


def program_name() -> str:
    """The app's name: PROGRAM_NAME from the launcher, else the script's file name."""
    return os.environ.get("PROGRAM_NAME") or Path(sys.argv[0] or "Python").stem


# ------------------------------------------------------------------ the app's window


def own_window() -> int:
    """This app's taskbar window: its own visible top-level window, else the classic console window."""
    if os.name != "nt":
        return 0
    import ctypes
    from ctypes import wintypes

    user = ctypes.WinDLL("user32", use_last_error=True)
    pid = os.getpid()
    found: List[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
    user.GetWindow.restype = wintypes.HWND

    def check(hwnd: int, _parameter: int) -> bool:
        # EnumWindows calls this for every top-level window; returning False stops the search.
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user.IsWindowVisible(hwnd) and not user.GetWindow(hwnd, 4):  # GW_OWNER
            found.append(hwnd)
            return False
        return True

    user.EnumWindows(callback_type(check), 0)
    if found:
        return found[0]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetConsoleWindow.restype = wintypes.HWND
    console = kernel.GetConsoleWindow() or 0
    name = ctypes.create_unicode_buffer(64)
    user.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    if console and user.GetClassNameW(console, name, 64) and name.value == "ConsoleWindowClass":
        return console
    return 0


def with_taskbar(action: Callable[[Any, Any, int], None]) -> bool:
    """Run action(taskbar, interface, hwnd) with Windows' ITaskbarList3; False if not possible.

    ITaskbarList3 is the Windows (COM) interface behind taskbar progress and badges. COM objects
    are reached through a table of function pointers (the "vtable"), declared below in its fixed
    order; only the methods used here get a real signature.
    """
    hwnd = own_window()
    if not hwnd:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        from pyapp.DONT_CHANGE.scripts.standalone import com_tools as com

        class Taskbar(ctypes.Structure):
            pass

        pointer = ctypes.POINTER(Taskbar)

        class VTable(ctypes.Structure):
            # ITaskbarList3 methods in their fixed order, up to SetOverlayIcon.
            _fields_ = (
                ("QueryInterface", com.UNUSED_METHOD),
                ("AddRef", com.UNUSED_METHOD),
                ("Release", com.METHOD(ctypes.c_ulong, pointer)),
                ("HrInit", com.METHOD(com.HRESULT, pointer)),
                ("AddTab", com.UNUSED_METHOD),
                ("DeleteTab", com.UNUSED_METHOD),
                ("ActivateTab", com.UNUSED_METHOD),
                ("SetActiveAlt", com.UNUSED_METHOD),
                ("MarkFullscreenWindow", com.UNUSED_METHOD),
                (
                    "SetProgressValue",
                    com.METHOD(com.HRESULT, pointer, wintypes.HWND, ctypes.c_ulonglong, ctypes.c_ulonglong),
                ),
                ("SetProgressState", com.METHOD(com.HRESULT, pointer, wintypes.HWND, ctypes.c_int)),
                ("RegisterTab", com.UNUSED_METHOD),
                ("UnregisterTab", com.UNUSED_METHOD),
                ("SetTabOrder", com.UNUSED_METHOD),
                ("SetTabActive", com.UNUSED_METHOD),
                ("ThumbBarAddButtons", com.UNUSED_METHOD),
                ("ThumbBarUpdateButtons", com.UNUSED_METHOD),
                ("ThumbBarSetImageList", com.UNUSED_METHOD),
                ("SetOverlayIcon", com.METHOD(com.HRESULT, pointer, wintypes.HWND, wintypes.HICON, wintypes.LPCWSTR)),
            )

        Taskbar._fields_ = [("vtable", ctypes.POINTER(VTable))]
        ole = ctypes.WinDLL("ole32", use_last_error=True)
        ole.CoCreateInstance.argtypes = [
            ctypes.POINTER(com.GUID),
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(com.GUID),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        ole.CoCreateInstance.restype = com.HRESULT
        clsid = com.guid("56FDF344-FD6D-11D0-958A-006097C9A090")  # the TaskbarList class
        iid = com.guid("EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF")  # its ITaskbarList3 interface
        initialized = com.co_initialize()
        try:
            raw = ctypes.c_void_p()
            com.check_hresult(
                ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(raw)),
                "CoCreateInstance(ITaskbarList3)",
            )
            taskbar = ctypes.cast(raw, pointer)
            interface = taskbar.contents.vtable.contents
            try:
                com.check_hresult(interface.HrInit(taskbar), "ITaskbarList3.HrInit")
                action(taskbar, interface, hwnd)
            finally:
                interface.Release(taskbar)
        finally:
            com.co_uninitialize(initialized)
        return True
    except Exception:
        return False


def load_icon(icon_path: str) -> int:
    """A 16 px icon handle from an .ico file, for the taskbar badge."""
    import ctypes
    from ctypes import wintypes

    user = ctypes.WinDLL("user32", use_last_error=True)
    user.LoadImageW.restype = wintypes.HANDLE
    user.LoadImageW.argtypes = [
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    icon = user.LoadImageW(None, str(icon_path), 1, 16, 16, 0x10) or 0  # IMAGE_ICON, LR_LOADFROMFILE
    if not icon:
        raise OSError(f"Cannot load icon: {icon_path}")
    return icon


# ------------------------------------------------------------------ system tray

_tray_controller: Any = None


def tray_controller(hwnd: int, name: str, icon_path: str) -> Any:
    """The tray controller for this window (one per app), started on first use.

    It is the launcher's own minimize-to-tray code (scripts/system_tray.py): while it runs, minimizing
    the window moves it into the tray; clicking the icon restores it; right-click offers Restore and
    Stop, and Stop asks the window to close as its X would.
    """
    global _tray_controller
    if _tray_controller is None or _tray_controller.target != hwnd:
        from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
        from pyapp.DONT_CHANGE.scripts.standalone.system_tray import MinimizeToTray

        def close_window() -> None:
            import ctypes

            ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE, like the window's X

        controller = MinimizeToTray(hwnd, name, icon_path, close_window, note_ignored)
        controller.start()
        _tray_controller = controller
    return _tray_controller


# ------------------------------------------------------------------ settings file


def watch_file(path: Path, on_change: Callable[[], None], interval: float = 1.0) -> None:
    """Call on_change() on a background thread whenever the file's modification time changes."""

    def stamp() -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    def watch() -> None:
        last = stamp()
        while True:
            time.sleep(interval)
            current = stamp()
            if current != last:
                last = current
                try:
                    on_change()
                except Exception:
                    traceback.print_exc()

    threading.Thread(target=watch, name="pyapp-settings-watch", daemon=True).start()


def reload_settings_module(path: Path) -> None:
    """Reload the imported "settings" module if it is this file, so settings.x shows the new values."""
    import importlib

    module = sys.modules.get("settings")
    module_file = getattr(module, "__file__", None)
    if module is not None and module_file and Path(module_file).resolve() == path.resolve():
        importlib.reload(module)


# ------------------------------------------------------------------ restart

SHORTCUT_TARGETS = {"wt": "W.bat", "conhost": "W.bat", "browser": "B.bat", "no_terminal": "N.bat"}

# Runs in a separate, detached Python: waits until the app's process has ended, gives the watchdog
# a moment to unregister the run, then starts the same shortcut target again.
RESTART_HELPER = r"""
import ctypes, subprocess, sys, time
pid, batch, app_id, folder = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
if handle:
    ctypes.windll.kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)
    ctypes.windll.kernel32.CloseHandle(handle)
time.sleep(1.5)
subprocess.Popen(["cmd.exe", "/d", "/c", batch, app_id], cwd=folder, creationflags=0x08000000)
"""


def start_after_exit(launch_mode: str, app_id: str) -> None:
    """Start a detached helper that starts the app again (same shortcut target) once this process ended."""
    batch = DONT_CHANGE / "B" / SHORTCUT_TARGETS.get(launch_mode, "W.bat")
    folder = os.environ.get("START_DIR") or str(Path.cwd())
    flags = 0x00000008 | 0x00000200 | 0x01000000  # DETACHED_PROCESS, NEW_PROCESS_GROUP, BREAKAWAY_FROM_JOB
    # A fixed helper with the paths as arguments; the restart runs the launcher's own shortcut target.
    subprocess.Popen(  # noqa: S603
        [sys.executable, "-I", "-c", RESTART_HELPER, str(os.getpid()), str(batch), app_id, folder],
        creationflags=flags,
        close_fds=True,
    )


# ------------------------------------------------------------------ forwarded starts


def alive(pid: int) -> bool:
    """True while the process with this ID runs."""
    if os.name != "nt":
        try:
            os.kill(pid, 0)  # signal 0 only checks; on Windows os.kill would end the process
        except OSError:
            return False
        return True
    import ctypes

    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    try:
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value == 259  # STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def listen_for_starts(callback: Callable[[List[str], str], None]) -> None:
    """App side: announce this process as a listener and call back for every forwarded start."""
    FORWARD_DIR.mkdir(parents=True, exist_ok=True)
    (FORWARD_DIR / f"listener-{os.getpid()}").write_text("", encoding="utf-8")

    def watch() -> None:
        while True:
            for message in sorted(FORWARD_DIR.glob(f"{os.getpid()}-*.json")):
                try:
                    data = json.loads(message.read_text(encoding="utf-8"))
                    message.unlink()
                except (OSError, ValueError):
                    continue
                try:
                    callback(list(data.get("arguments", [])), str(data.get("start_folder", "")))
                except Exception:
                    traceback.print_exc()
            time.sleep(0.3)

    threading.Thread(target=watch, name="pyapp-new-start", daemon=True).start()


def forward_start(arguments: List[str], start_folder: str) -> int:
    """Launcher side: pass a cancelled start's arguments to every running listener; returns how many."""
    if not FORWARD_DIR.is_dir():
        return 0
    delivered = 0
    for listener in FORWARD_DIR.glob("listener-*"):
        try:
            pid = int(listener.name.split("-", 1)[1])
        except ValueError:
            continue
        if not alive(pid):
            with contextlib.suppress(OSError):
                listener.unlink()
            continue
        target = FORWARD_DIR / f"{pid}-{time.time_ns()}-{uuid.uuid4().hex[:6]}.json"
        # Written under another name first, so the listener never reads a half-written file.
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps({"arguments": list(arguments), "start_folder": start_folder}), encoding="utf-8")
        temporary.replace(target)
        delivered += 1
    return delivered

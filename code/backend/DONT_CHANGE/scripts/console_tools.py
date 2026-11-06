"""Windows console appearance and interactive messages."""

from __future__ import annotations

import os
import sys
from typing import Any, TextIO

from backend.DONT_CHANGE.scripts.diagnostics import note_ignored

ANSI_WARN = "\x1b[1;37;41m"
ANSI_SUCCESS = "\x1b[1;37;42m"
ANSI_RESET = "\033[0m"


def enable_ansi() -> None:
    """Turn on ANSI color processing for this console (classic conhost needs it explicitly)."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        note_ignored("enable_ansi")


def show_console() -> None:
    """Restore and focus this process's console window (shortcuts start it minimized)."""
    unminimize_terminal()
    foreground_terminal()


def _styled(msg: Any, style: str) -> str:
    """Color only for an interactive console; redirected output stays plain."""
    try:
        interactive = sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        interactive = False
    if not interactive:
        return str(msg)
    enable_ansi()
    return f"{style}{msg}{ANSI_RESET}"


def print_warn(msg: Any, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a warning-styled console message."""
    if msg is not None:
        print(_styled(msg, ANSI_WARN), sep=sep, end=end)


def input_warn(msg: str) -> str:
    """Prompt for input using warning console styling."""
    return input(_styled(msg, ANSI_WARN))


def print_success(msg: Any, sep: str | None = " ", end: str | None = "\n") -> None:
    """Print a success-styled console message."""
    if msg is not None:
        print(_styled(msg, ANSI_SUCCESS), sep=sep, end=end)


def set_terminal_title(title: str | None) -> None:
    """Set the Windows console title when supplied, ignoring unavailable console APIs."""
    if title is None:
        return

    try:
        import ctypes

        clean_name = title.replace("\r\n", "").replace("\r", "")
        ctypes.windll.kernel32.SetConsoleTitleW(clean_name)
    except Exception:
        note_ignored("set_terminal_title")


def set_terminal_icon(icon_path: str | None) -> None:
    """Best-effort icon update of the current Windows terminal icon"""
    if icon_path in ("", None):
        return
    else:
        icon_path = os.path.normpath(icon_path)

    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type:ignore
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [
            wintypes.HWND,
            ctypes.c_uint,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        user32.SendMessageW.restype = ctypes.c_size_t
        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL

        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        LR_DEFAULTSIZE = 0x0040
        SM_CXSMICON = 49
        SM_CYSMICON = 50
        SM_CXICON = 11
        SM_CYICON = 12
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        def _load_icon(width: int, height: int) -> int:
            """Load the requested ICO size, falling back to the image's default size."""
            icon = user32.LoadImageW(
                None, icon_path, IMAGE_ICON, width, height, LR_LOADFROMFILE
            )
            if not icon:
                icon = user32.LoadImageW(
                    None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
                )
            return int(icon or 0)

        small_icon = _load_icon(
            user32.GetSystemMetrics(SM_CXSMICON),
            user32.GetSystemMetrics(SM_CYSMICON),
        )
        large_icon = _load_icon(
            user32.GetSystemMetrics(SM_CXICON),
            user32.GetSystemMetrics(SM_CYICON),
        )
        if small_icon == 0 and large_icon == 0:
            return

        if small_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
        if large_icon:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, large_icon)
        user32.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    except Exception:
        note_ignored("set_terminal_icon")


def set_terminal_app_id(app_id: str) -> None:
    """Try to set System.AppUserModel.ID on the terminal window itself."""

    if not app_id:
        return
    try:
        import ctypes
        from ctypes import wintypes

        from backend.DONT_CHANGE.scripts import com_tools as com

        hwnd = int(ctypes.windll.kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        shell32.SHGetPropertyStoreForWindow.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(com.GUID),
            ctypes.POINTER(com.PropertyStorePointer),
        ]
        shell32.SHGetPropertyStoreForWindow.restype = com.HRESULT
        should_uninitialize = com.co_initialize()
        try:
            store = com.PropertyStorePointer()
            com.check_hresult(
                shell32.SHGetPropertyStoreForWindow(
                    wintypes.HWND(hwnd), ctypes.byref(com.IID_PROPERTY_STORE), ctypes.byref(store)
                ),
                f"SHGetPropertyStoreForWindow for hwnd 0x{hwnd:016X}",
            )
            com.set_app_user_model_id(store, app_id)
        finally:
            com.co_uninitialize(should_uninitialize)
        # Redraw the frame so the taskbar picks up the new identity.
        SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x1, 0x2, 0x4, 0x10, 0x20
        ctypes.WinDLL("user32", use_last_error=True).SetWindowPos(
            hwnd, None, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        )
    except Exception:
        note_ignored("set_terminal_app_id")


def unminimize_terminal() -> None:
    """Restore the current console window when Windows exposes its handle."""
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # 9 means unminimized
    except Exception:
        note_ignored("unminimize_terminal")


def foreground_terminal() -> None:
    """Ask Windows to bring the current console window to the foreground."""
    try:
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        hwnd = int(kernel32.GetConsoleWindow() or 0)
        if not hwnd:
            return
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        note_ignored("foreground_terminal")


def enable_unminimize_and_foreground_terminal_on_first_print() -> None:
    """Wrap stdout and stderr so their first nonempty output restores the console."""

    class unminimize_plus_foreground_terminal_on_first_output:
        """Unminimize a minimized terminal and set to foreground when output is written for the first time."""

        def __init__(self, stream: TextIO) -> None:
            """Store the wrapped output stream and track whether the console has been restored."""
            self.stream = stream
            self._restored = False

        def _restore_if_needed(self, data: object) -> None:
            """Restore and foreground the console once, on the first nonempty write."""
            if self._restored or data in ("", b""):
                return
            self._restored = True
            unminimize_terminal()
            foreground_terminal()

        def write(self, data: str) -> int:
            """Write text to the wrapped stream or terminal target."""
            self._restore_if_needed(data)
            return self.stream.write(data)

        def flush(self) -> None:
            """Flush the wrapped stream when supported."""
            if hasattr(self.stream, "flush"):
                self.stream.flush()

        def isatty(self) -> bool:
            """Return whether the wrapped stream behaves like a terminal."""
            return bool(getattr(self.stream, "isatty", lambda: False)())

        def writable(self) -> bool:
            """Return whether the wrapped stream accepts writes."""
            return True

        def fileno(self) -> int:
            """Return the wrapped stream file descriptor."""
            if hasattr(self.stream, "fileno"):
                return self.stream.fileno()
            raise OSError("Underlying stream does not support fileno()")

        def __getattr__(self, name: str) -> Any:
            """Forward unknown attribute lookups to the wrapped stream."""
            return getattr(self.stream, name)

    # this will unminimize and foreground on first print/error
    sys.stdout = unminimize_plus_foreground_terminal_on_first_output(sys.stdout)  # type:ignore
    sys.stderr = unminimize_plus_foreground_terminal_on_first_output(sys.stderr)  # type:ignore


def set_terminal_colors(colors: str | None) -> None:
    """colors is in format of windows terminal colors"""
    if colors:
        try:
            import subprocess

            subprocess.run(["cmd.exe", "/c", "color", colors], check=False)
        except Exception:
            note_ignored("set_terminal_colors")

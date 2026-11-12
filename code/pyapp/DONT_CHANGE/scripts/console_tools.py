"""Windows console appearance and interactive messages."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Any, Iterable, List, Optional, TextIO, Tuple, Union

from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored

# Message styles. Every launcher window uses the same few, so they look alike:
#   print_heading   "── Title ────"              sections
#   print_step      "» Installing packages ..."  something that may take a while
#   print_info      grey text                    notes and details
#   print_success   " OK " badge + text          a finished task
#   print_warn      " ! " badge + text           something to look at; the task goes on
#   print_error     " ERROR " badge + text       the task failed
#   ask / wait_for_enter / print_choices         questions and menus
ANSI_ERROR = "\x1b[1;37;41m"  # white on red
ANSI_SUCCESS = "\x1b[1;37;42m"  # white on green
ANSI_WARNING = "\x1b[1;30;43m"  # black on yellow
ANSI_HEADING = "\x1b[1;36m"  # bold cyan
ANSI_GOOD = "\x1b[32m"  # green
ANSI_DIM = "\x1b[90m"  # grey
ANSI_BOLD = "\x1b[1m"
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


def styled(msg: Any, style: str) -> str:
    """Color only for an interactive console; redirected output stays plain."""
    try:
        interactive = sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        interactive = False
    if not interactive:
        return str(msg)
    enable_ansi()
    return f"{style}{msg}{ANSI_RESET}"


def print_heading(title: str, width: int = 72) -> None:
    """Print a section heading: a blank line, then "── title ───..."."""
    print()
    print(styled(f"── {title} " + "─" * max(3, width - len(title) - 4), ANSI_HEADING))


def _badge_lines(label: str, style: str, msg: Any) -> str:
    """A colored label before the first line; further lines are indented to match."""
    lines = str(msg).split("\n")
    indent = " " * (len(label) + 3)
    return "\n".join([styled(f" {label} ", style) + " " + lines[0]] + [indent + line for line in lines[1:]])


def print_step(msg: Any) -> None:
    """A step that may take a while (installing, downloading, building)."""
    print(styled("»", ANSI_HEADING) + " " + str(msg), flush=True)


def print_info(msg: Any) -> None:
    """A note or detail."""
    print(styled(msg, ANSI_DIM), flush=True)


def print_success(msg: Any) -> None:
    """A finished task."""
    print(_badge_lines("OK", ANSI_SUCCESS, msg), flush=True)


def print_warn(msg: Any) -> None:
    """Something to look at; the task goes on."""
    print(_badge_lines("!", ANSI_WARNING, msg), flush=True)


def print_error(msg: Any, file: Optional[TextIO] = None) -> None:
    """The task failed."""
    print(_badge_lines("ERROR", ANSI_ERROR, msg), file=file or sys.stdout, flush=True)


def ask(question: str) -> str:
    """Ask for an answer on the same line."""
    return input(styled("?", ANSI_HEADING) + " " + styled(question.rstrip(), ANSI_BOLD) + " ")


def wait_for_enter(message: str = "Press Enter to close this window.") -> None:
    """Keep the window open until Enter (no-op without an interactive console)."""
    with contextlib.suppress(EOFError, KeyboardInterrupt):
        input(styled(message, ANSI_DIM))


def print_fields(rows: Iterable[Union[Tuple[str, object], Tuple[str, object, bool]]], indent: int = 2) -> None:
    """Aligned "label   value" rows; a value whose third item is False is highlighted as a problem."""
    normalized_rows: List[Tuple[str, object, bool]] = []
    for row in rows:
        if len(row) == 3:
            label, value, ok = row
        else:
            label, value = row
            ok = True
        normalized_rows.append((label, value, ok))
    rows = normalized_rows
    width = max((len(label) for label, _, _ in rows), default=0)
    for label, value, ok in rows:
        print(
            " " * indent
            + styled(label.ljust(width), ANSI_DIM)
            + "  "
            + (str(value) if ok else styled(value, ANSI_BOLD + "\x1b[33m"))
        )


def print_choices(options: Iterable[object], start: int = 1) -> None:
    """A numbered list: "  1  first option"."""
    for index, option in enumerate(options, start):
        print(f"  {styled(str(index).rjust(2), ANSI_HEADING)}  {option}")


def print_settings_diff(lines: Iterable[str]) -> None:
    """The changes edit_settings made: removed lines in red, added lines in green."""
    for line in lines:
        print("  " + styled(line, "\x1b[31m" if line.startswith("-") else ANSI_GOOD))


def set_terminal_title(title: Optional[str]) -> None:
    """Set the Windows console title when supplied, ignoring unavailable console APIs."""
    if title is None:
        return

    try:
        import ctypes

        clean_name = title.replace("\r", "").replace("\n", "")
        ctypes.windll.kernel32.SetConsoleTitleW(clean_name)
    except Exception:
        note_ignored("set_terminal_title")


def set_terminal_icon(icon_path: Optional[str]) -> None:
    """Best-effort icon update of the current Windows terminal icon"""
    if icon_path in ("", None):
        return
    icon_path = os.path.normpath(icon_path)
    if in_browser_terminal():
        browser_terminal_ui(icon=icon_path)  # the page's favicon
        return

    import ctypes
    from ctypes import wintypes

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
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
            icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, width, height, LR_LOADFROMFILE)
            if not icon:
                icon = user32.LoadImageW(None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
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

        from pyapp.DONT_CHANGE.scripts import com_tools as com

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
        # Only a minimized window: SW_RESTORE would also shrink a window the user maximized.
        if not hwnd or not ctypes.windll.user32.IsIconic(hwnd):
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
    sys.stdout = unminimize_plus_foreground_terminal_on_first_output(sys.stdout)
    sys.stderr = unminimize_plus_foreground_terminal_on_first_output(sys.stderr)


def set_terminal_colors(colors: Optional[str]) -> None:
    """colors is in format of windows terminal colors"""
    if colors:
        import re

        if not isinstance(colors, str) or not re.fullmatch(r"[0-9A-Fa-f]{1,2}", colors):
            raise ValueError("Terminal colors must contain one or two hexadecimal digits.")
        if in_browser_terminal():
            # Like `color`, this recolors everything with the default colors, including what was printed.
            browser_terminal_ui(colors=colors)
            return
        try:
            import subprocess

            # The color argument is restricted to hex digits before reaching cmd.exe.
            from pyapp.DONT_CHANGE.backend_settings import CMD_EXE

            subprocess.run([CMD_EXE, "/c", "color", colors], check=False)  # noqa: S603
        except Exception:
            note_ignored("set_terminal_colors")


# ---------------------------------------------------------------- browser terminal
#
# The browser terminal shortcut shows the console as a pseudoconsole in the browser (the
# browser_terminal package). Titles and text reach the page through it, but the window icon and
# the `color` command do not: those requests go through the package's ui module instead.


def in_browser_terminal() -> bool:
    """True in a console shown by the browser terminal."""
    try:
        from pyapp.DONT_CHANGE.backend_settings import BROWSER_UI_ENV_VAR
        from pyapp.DONT_CHANGE.browser_terminal import ui

        return ui.inside(BROWSER_UI_ENV_VAR)
    except Exception:
        note_ignored("in_browser_terminal")
        return False


def browser_terminal_ui(
    icon: Optional[str] = None, colors: Optional[str] = None, notify: Optional[str] = None, failed: bool = False
) -> None:
    """Ask the browser terminal for an icon (file), colors (a `color` argument such as "4F") or a notification."""
    try:
        from pyapp.DONT_CHANGE.backend_settings import BROWSER_UI_ENV_VAR
        from pyapp.DONT_CHANGE.browser_terminal import ui

        ui.request(
            BROWSER_UI_ENV_VAR,
            icon=icon,
            colors=ui.colors_from_code(colors) if colors else None,
            notify=notify,
            failed=failed,
        )
    except Exception:
        note_ignored("browser_terminal_ui")


# ---------------------------------------------------------------- editor

# Editors whose "code" command on PATH is a batch file next to the real executable.
_VSCODE_EXECUTABLES = ("Code.exe", "Code - Insiders.exe", "VSCodium.exe", "Cursor.exe")


def _editor_executable() -> Optional[str]:
    """VS Code (or a fork) found via the "code" command, preferring the .exe over bin\\code.cmd."""
    import shutil

    found = shutil.which("code")
    if not found:
        return None
    if found.lower().endswith((".cmd", ".bat")):
        # bin\code.cmd sits one folder below Code.exe. Starting the .exe directly avoids
        # cmd.exe parsing the file path (a folder like "R&D" would otherwise break it).
        install_dir = str(Path(os.path.normpath(str(Path(found).absolute()))).parent.parent)
        for name in _VSCODE_EXECUTABLES:
            candidate = str(Path(install_dir) / name)
            if Path(candidate).is_file():
                return candidate
    return found


def open_in_editor(path: str) -> None:
    """Open a file preferably in VS Code with fallback in Windows notepad. Lazily imports subprocess."""
    import subprocess

    if not Path(path).exists():
        raise FileNotFoundError(path)
    # The editor keeps running after the launcher; do not hand it the launcher's variables
    # (they would leak into its integrated terminals), or one that makes Code.exe act as Node.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("PYAPP_") and key.upper() != "ELECTRON_RUN_AS_NODE"
    }
    editor = _editor_executable()
    if editor is None:
        # Launching the local editor or Windows color command is intentional.
        from pyapp.DONT_CHANGE.backend_settings import NOTEPAD_EXE

        subprocess.Popen([NOTEPAD_EXE, path], env=env)  # noqa: S603
    elif editor.lower().endswith((".cmd", ".bat")):
        # Batch files run through cmd.exe: always quote, so & ( ) ^ in the path stay literal.
        # Launching the local editor or Windows color command is intentional.
        subprocess.Popen(f'"{editor}" "{path}"', env=env)  # noqa: S603
    else:
        # Launching the local editor or Windows color command is intentional.
        subprocess.Popen([editor, path], env=env)  # noqa: S603

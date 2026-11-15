"""Host capability boundaries and native window styles on a disposable Windows window."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import unittest
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from project_location import CODE

# isort: split

from pyapp.DONT_CHANGE.actions.start_program import wt_command
from pyapp.DONT_CHANGE.scripts import terminal_window as window
from pyapp.DONT_CHANGE.scripts.errors import SettingsError


def settings(**overrides: object) -> SimpleNamespace:
    return SimpleNamespace(
        **{
            "terminal_alpha": None,
            "always_on_top": False,
            "hide_minimize_button": False,
            "hide_maximize_button": False,
            "confirm_on_close": "close",
            "program_name": "Test",
            **overrides,
        }
    )


class HostCapabilities(unittest.TestCase):
    def test_close_mode_support_is_explicit(self):
        supported = {"conhost": {"close", "block"}, "wt": {"close"}, "browser": {"close", "prompt", "hide"}}
        for host, modes in supported.items():
            for mode in ("close", "prompt", "hide", "block"):
                with self.subTest(host=host, mode=mode):
                    if mode in modes:
                        window.validate_close_mode(settings(confirm_on_close=mode), host)
                    else:
                        with self.assertRaisesRegex(SettingsError, "confirm_on_close"):
                            window.validate_close_mode(settings(confirm_on_close=mode), host)
        window.validate_close_mode(settings(confirm_on_close="block"), "no_terminal")

    def test_defaults_and_browser_never_touch_windows(self):
        with mock.patch.object(window.ctypes, "WinDLL") as api:
            for host in ("conhost", "wt", "browser", "no_terminal"):
                window.configure(settings(), host)
            window.configure(settings(terminal_alpha=0.8, always_on_top=True), "browser")
        api.assert_not_called()

    def test_native_customization_uses_a_dedicated_wt_window(self):
        self.assertFalse(window.needs_window(settings()))
        for options in ({"terminal_alpha": 1}, {"terminal_alpha": 0.8}, {"always_on_top": True}):
            self.assertTrue(window.needs_window(settings(**options)))
        command = wt_command("A; B", "", ["python.exe", "C:\\R;D\\run.py"], dedicated_window=True)
        self.assertEqual(command[:5], ["wt.exe", "--window", "new", "new-tab", "--useApplicationTitle"])
        self.assertEqual(command[5:], ["--title", "A\\; B", "python.exe", "C:\\R\\;D\\run.py"])


@unittest.skipUnless(os.name == "nt", "Windows only")
class NativeWindow(unittest.TestCase):
    def test_classic_watchdog_can_configure_its_console(self):
        with tempfile.TemporaryDirectory() as folder:
            result = Path(folder) / "result.txt"
            script = (
                "import sys; from pathlib import Path; from types import SimpleNamespace; "
                f"sys.path.insert(0, {str(CODE)!r}); "
                "from pyapp.DONT_CHANGE.scripts.terminal_window import configure; "
                "s = SimpleNamespace(terminal_alpha=0.8, always_on_top=True, "
                "hide_minimize_button=True, hide_maximize_button=True, allow_minimize=False, allow_maximize=False, confirm_on_close='block'); "
                "configure(s, 'conhost'); "
                "from pyapp.DONT_CHANGE.scripts.taskbar_status import terminal_window, set_progress, flash; "
                "hwnd = terminal_window(); assert hwnd; "
                "[set_progress(hwnd, state) for state in (1, 2, 4, 0)]; flash(hwnd); "
                f"Path({str(result)!r}).write_text('configured', encoding='utf-8')"
            )
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 7  # minimized; only the disposable console is changed
            conhost = str(Path(os.environ.get("WINDIR", "C:\\Windows")) / "System32" / "conhost.exe")
            python = getattr(sys, "_base_executable", sys.executable)
            # Only the system conhost, this interpreter and fixed test code are executed.
            with subprocess.Popen([conhost, python, "-c", script], startupinfo=startup) as child:  # noqa: S603
                try:
                    self.assertEqual(child.wait(timeout=15), 0)
                finally:
                    if child.poll() is None:
                        child.kill()
            self.assertEqual(result.read_text(encoding="utf-8"), "configured")

    def test_alpha_caption_buttons_topmost_and_block_close(self):
        user = ctypes.WinDLL("user32", use_last_error=True)
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
        user.DestroyWindow.argtypes = [wintypes.HWND]
        user.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user.GetWindowLongW.restype = wintypes.LONG
        user.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
        user.GetSystemMenu.restype = wintypes.HMENU
        user.GetMenuState.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
        user.GetMenuState.restype = wintypes.UINT
        user.GetLayeredWindowAttributes.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.BYTE),
            ctypes.POINTER(wintypes.DWORD),
        ]
        # A hidden, disposable overlapped window: no changes to the developer's own terminal.
        hwnd = user.CreateWindowExW(
            0, "STATIC", "PyApp window settings test", 0x00CF0000, 0, 0, 200, 100, None, None, None, None
        )
        self.assertTrue(hwnd, ctypes.get_last_error())
        self.addCleanup(user.DestroyWindow, hwnd)
        for alpha in (0.8, 0.001, 1):
            window.apply_window_settings(
                hwnd,
                settings(
                    terminal_alpha=alpha,
                    always_on_top=True,
                    hide_minimize_button=True,
                    hide_maximize_button=True,
                    confirm_on_close="block",
                ),
                classic=True,
            )
            style = user.GetWindowLongW(hwnd, window.GWL_STYLE)
            self.assertFalse(style & (window.WS_MINIMIZEBOX | window.WS_MAXIMIZEBOX))
            self.assertTrue(user.GetWindowLongW(hwnd, window.GWL_EXSTYLE) & 0x00000008)  # WS_EX_TOPMOST
            menu = user.GetSystemMenu(hwnd, False)
            self.assertTrue(user.GetMenuState(menu, window.SC_CLOSE, 0) & window.MF_GRAYED)
            color, actual_alpha, flags = wintypes.DWORD(), wintypes.BYTE(), wintypes.DWORD()
            self.assertTrue(
                user.GetLayeredWindowAttributes(
                    hwnd, ctypes.byref(color), ctypes.byref(actual_alpha), ctypes.byref(flags)
                )
            )
            self.assertEqual(actual_alpha.value, max(1, round(alpha * 255)))
            self.assertEqual(flags.value, window.LWA_ALPHA)
        window.apply_window_settings(hwnd, settings(allow_minimize=False, allow_maximize=False), classic=True)
        menu = user.GetSystemMenu(hwnd, False)
        for command in (window.SC_MINIMIZE, window.SC_MAXIMIZE):
            self.assertTrue(user.GetMenuState(menu, command, 0) & window.MF_GRAYED)


if __name__ == "__main__":
    unittest.main()

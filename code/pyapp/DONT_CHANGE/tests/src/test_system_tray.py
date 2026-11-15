"""Minimize-to-tray recovery, repeat notifications, owner safety and real Windows message-loop cleanup."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from project_location import CODE

# isort: split

from pyapp.DONT_CHANGE.runtime import bg_watchdog
from pyapp.DONT_CHANGE.scripts import config, terminal_window
from pyapp.DONT_CHANGE.scripts import system_tray as tray


@unittest.skipUnless(os.name == "nt", "Windows notification area only")
class TrayLogicTests(unittest.TestCase):
    def controller(self):
        # No desktop mutation: use a fake native API, but real notification structures/callback logic.
        with mock.patch.object(ctypes, "WinDLL"):
            result = tray.MinimizeToTray(123, "Example", "icon.ico", mock.Mock())
        user, shell = mock.Mock(), mock.Mock()
        result.user = user
        result.shell = shell
        result.owner_pid = 10
        result.hwnd = 456
        result.icon = 789
        result.restart_message = 987
        result.added = True
        owner_patch = mock.patch.object(result, "_owner", return_value=10)
        owner = owner_patch.start()
        self.addCleanup(owner_patch.stop)
        stop = mock.Mock()
        result.on_stop = stop
        return result, user, shell, owner, stop

    def test_each_cycle_notifies_once_and_clicking_notification_restores(self):
        controller, _user, shell, _owner, _stop = self.controller()
        controller.minimize()
        controller.minimize()  # timer ticks while already hidden must not spam notifications
        self.assertTrue(controller.hidden)
        self.assertEqual(shell.Shell_NotifyIconW.call_count, 1)
        args = shell.Shell_NotifyIconW.call_args[0]
        self.assertEqual(args[0], tray.NIM_MODIFY)
        data = args[1]._obj
        self.assertIn("hidden-icons arrow", data.szInfo)
        self.assertIn("restore", data.szInfo)
        self.assertLess(len(data.szInfo), 256)
        controller._message(456, tray.WM_TRAY, 0, (1 << 16) | 0x405)
        self.assertFalse(controller.hidden)
        self.assertFalse(controller.added)
        self.assertEqual(shell.Shell_NotifyIconW.call_args[0][0], tray.NIM_DELETE)
        controller.minimize()
        self.assertTrue(controller.added)
        self.assertEqual(
            [call[0][0] for call in shell.Shell_NotifyIconW.call_args_list],
            [tray.NIM_MODIFY, tray.NIM_DELETE, tray.NIM_ADD, tray.NIM_SETVERSION, tray.NIM_MODIFY],
        )

    def test_never_hides_without_icon_or_when_handle_owner_changed(self):
        controller, user, shell, owner, _stop = self.controller()
        controller.added = False
        shell.Shell_NotifyIconW.return_value = False
        with self.assertRaises(OSError):
            controller.minimize()
        user.ShowWindow.assert_not_called()
        controller.added = True
        owner.return_value = 20
        controller.minimize()
        user.ShowWindow.assert_not_called()

    def test_long_non_bmp_program_names_fit_windows_text_fields(self):
        controller, _user, shell, _owner, _stop = self.controller()
        controller.name = "\U0001f40d" * 100
        self.assertLessEqual(len(controller._data(tray.NIF_TIP).szTip.encode("utf-16-le")), 127 * 2)
        controller.minimize()
        data = shell.Shell_NotifyIconW.call_args[0][1]._obj
        self.assertLessEqual(len(data.szInfoTitle.encode("utf-16-le")), 63 * 2)

    def test_rejected_notification_restores_instead_of_silently_hiding(self):
        controller, user, shell, _owner, _stop = self.controller()
        shell.Shell_NotifyIconW.return_value = False
        with mock.patch.object(tray, "note_ignored"):
            controller.minimize()
        self.assertFalse(controller.hidden)
        self.assertEqual(
            user.ShowWindow.call_args_list, [mock.call(123, tray.SW_HIDE), mock.call(123, tray.SW_RESTORE)]
        )

    def test_external_restore_removes_the_tray_icon(self):
        controller, user, shell, _owner, _stop = self.controller()
        controller.hidden = True
        user.IsWindowVisible.return_value = True
        controller._tick()
        self.assertFalse(controller.hidden)
        self.assertFalse(controller.added)
        self.assertEqual(shell.Shell_NotifyIconW.call_args[0][0], tray.NIM_DELETE)

    def test_explorer_restart_restores_without_recreating_a_visible_windows_icon(self):
        controller, user, shell, _owner, _stop = self.controller()
        controller.hidden = True
        controller._message(456, controller.restart_message, 0, 0)
        self.assertFalse(controller.hidden)
        self.assertEqual(user.ShowWindow.call_args[0], (123, tray.SW_RESTORE))
        self.assertFalse(controller.added)
        shell.Shell_NotifyIconW.assert_not_called()

    def test_stop_menu_targets_only_the_current_app_and_marks_requested_stop(self):
        controller, user, _shell, _owner, stop = self.controller()
        user.TrackPopupMenu.return_value = 2
        controller._menu()
        stop.assert_called_once()
        with tempfile.TemporaryDirectory() as folder:
            child = mock.Mock(pid=123)
            child.poll.return_value = None
            with mock.patch.object(bg_watchdog, "end_started_app") as end:
                bg_watchdog.stop_from_tray(child, Path(folder), 0)
                end.assert_called_once_with(child)
            self.assertTrue((Path(folder) / bg_watchdog.paths.STOP_REQUEST_FILE_NAME).is_file())

    def test_setting_defaults_off_validates_boolean_and_isolates_wt(self):
        s = config.settings()
        defaults = SimpleNamespace(program_name="Test")
        config.fill_missing_settings(defaults)
        self.assertFalse(defaults.replace_minimize_with_minimize_to_system_tray)
        with mock.patch.object(s, "replace_minimize_with_minimize_to_system_tray", "yes"), self.assertRaisesRegex(
            config.SettingsError, "replace_minimize_with_minimize_to_system_tray"
        ):
            config.validate(s)
        with mock.patch.object(s, "replace_minimize_with_minimize_to_system_tray", True):
            self.assertTrue(terminal_window.needs_window(s))


@unittest.skipUnless(os.name == "nt", "Windows notification area only")
class NativeTrayTests(unittest.TestCase):
    def test_structure_matches_windows_and_live_conhost_can_minimize_restore_and_clean_up(self):
        self.assertEqual(ctypes.sizeof(tray.NOTIFYICONDATA), 976 if ctypes.sizeof(ctypes.c_void_p) == 8 else 956)
        with tempfile.TemporaryDirectory() as folder:
            result = Path(folder) / "result.txt"
            script = Path(folder) / "probe.py"
            script.write_text(
                "import ctypes, sys, time, traceback\n"
                "from ctypes import wintypes\nfrom pathlib import Path\n"
                f"sys.path.insert(0, {str(CODE)!r})\n"
                "from pyapp.DONT_CHANGE.scripts.system_tray import MinimizeToTray, WM_TRAY, SW_RESTORE\n"
                "user = ctypes.WinDLL('user32', use_last_error=True)\n"
                "kernel = ctypes.WinDLL('kernel32', use_last_error=True)\n"
                "kernel.GetConsoleWindow.restype = wintypes.HWND\n"
                "user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]\n"
                "user.IsWindowVisible.argtypes = [wintypes.HWND]\n"
                "user.IsIconic.argtypes = [wintypes.HWND]\n"
                "user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]\n"
                "hwnd = kernel.GetConsoleWindow()\n"
                "controller = MinimizeToTray(hwnd, 'PyApp tray test', '', lambda: None)\n"
                "def wait(test):\n"
                "    deadline = time.monotonic() + 5\n"
                "    while not test() and time.monotonic() < deadline: time.sleep(.02)\n"
                "    assert test(), 'native window state did not change'\n"
                "try:\n"
                "    controller.start()\n"
                "    for _ in range(2):\n"
                "        user.ShowWindow(hwnd, 6)\n"
                "        wait(lambda: controller.hidden and not user.IsWindowVisible(hwnd))\n"
                "        user.PostMessageW(controller.hwnd, WM_TRAY, 0, (1 << 16) | 0x405)\n"
                "        wait(lambda: not controller.hidden and not controller.added and user.IsWindowVisible(hwnd) and not user.IsIconic(hwnd))\n"
                "    user.ShowWindow(hwnd, 6)\n"
                "    wait(lambda: controller.hidden)\n"
                "    controller.close()\n"
                "    assert user.IsWindowVisible(hwnd), 'cleanup left terminal hidden'\n"
                "    assert not controller.thread.is_alive() and not controller.added\n"
                f"    Path({str(result)!r}).write_text('passed', encoding='utf-8')\n"
                "except BaseException:\n"
                f"    Path({str(result)!r}).write_text(traceback.format_exc(), encoding='utf-8')\n"
                "finally:\n    controller.close()\n",
                encoding="utf-8",
            )
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 7
            conhost = str(Path(os.environ.get("WINDIR", "C:\\Windows")) / "System32" / "conhost.exe")
            python = getattr(sys, "_base_executable", sys.executable)
            # Fixed system conhost/current interpreter and a test script created just above.
            with subprocess.Popen([conhost, python, str(script)], startupinfo=startup) as child:  # noqa: S603
                try:
                    child.wait(timeout=25)
                finally:
                    if child.poll() is None:
                        child.kill()
            answer = result.read_text(encoding="utf-8")
            self.assertEqual(answer, "passed", answer)


if __name__ == "__main__":
    unittest.main()

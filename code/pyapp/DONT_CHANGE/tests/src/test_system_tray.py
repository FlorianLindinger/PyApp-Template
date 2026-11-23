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
from pyapp.DONT_CHANGE.scripts.standalone import system_tray as tray


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
        self.assertEqual(data.szInfoTitle, "Example")
        self.assertEqual(data.hBalloonIcon, controller.icon)
        self.assertEqual(data.dwInfoFlags & 0xF, 4)  # NIIF_USER, rather than Windows' generic info icon
        self.assertTrue(data.dwInfoFlags & 0x20)  # NIIF_LARGE_ICON
        self.assertTrue(data.uFlags & 0x40)  # NIF_REALTIME: do not queue a stale restore notice
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
        controller.on_error = mock.Mock()
        controller.minimize()
        controller.on_error.assert_any_call("send minimize-to-tray notification")
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

    def test_duplicate_restore_keeps_an_already_visible_maximized_window(self):
        controller, user, _shell, _owner, _stop = self.controller()
        user.IsWindowVisible.return_value = True
        user.IsIconic.return_value = False
        controller.restore()
        controller.restore()
        user.ShowWindow.assert_not_called()
        self.assertFalse(controller.added)

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
                "from pyapp.DONT_CHANGE.scripts.standalone.system_tray import MinimizeToTray, WM_TRAY, SW_RESTORE, NIF_INFO, NIF_REALTIME, NIIF_USER\n"
                "user = ctypes.WinDLL('user32', use_last_error=True)\n"
                "kernel = ctypes.WinDLL('kernel32', use_last_error=True)\n"
                "kernel.GetConsoleWindow.restype = wintypes.HWND\n"
                "user.IsWindowVisible.argtypes = [wintypes.HWND]\n"
                "user.IsIconic.argtypes = [wintypes.HWND]\n"
                "user.IsZoomed.argtypes = [wintypes.HWND]\n"
                "user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]\n"
                "user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]\n"
                "user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM, wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]\n"
                "user.SendMessageTimeoutW.restype = ctypes.c_ssize_t\n"
                "hwnd = kernel.GetConsoleWindow()\n"
                f"icon_path = {str(CODE / 'pyapp/icons/icon.ico')!r}\n"
                # Keep real icon/message-loop operations, intercept only the visible balloon request.
                "class QuietTray(MinimizeToTray):\n"
                "    def __init__(self, *args):\n"
                "        super().__init__(*args)\n"
                "        self.notices = 0\n"
                "        native_notify = self.shell.Shell_NotifyIconW\n"
                "        def notify(command, pointer):\n"
                "            data = pointer._obj\n"
                "            if data.uFlags & NIF_INFO:\n"
                "                assert data.szInfoTitle == self.name and data.hBalloonIcon == self.icon\n"
                "                assert data.uFlags & NIF_REALTIME and data.dwInfoFlags & 0xF == NIIF_USER\n"
                "                self.notices += 1\n"
                "                return True\n"
                "            return native_notify(command, pointer)\n"
                "        self.shell.Shell_NotifyIconW = notify\n"
                # Delay dispatch to reproduce a busy desktop: a fixed sleep cannot acknowledge a callback.
                "class DelayedTray(QuietTray):\n"
                "    def _message(self, hwnd, message, wparam, lparam):\n"
                "        if message == WM_TRAY: time.sleep(.15)\n"
                "        return super()._message(hwnd, message, wparam, lparam)\n"
                "controller = DelayedTray(hwnd, 'PyApp tray test', icon_path, lambda: None)\n"
                "def send(message, lparam=0):\n"
                "    result = ctypes.c_size_t()\n"
                "    assert user.SendMessageTimeoutW(controller.hwnd, message, 0, lparam, 2, 5000, ctypes.byref(result)), 'native callback timed out'\n"
                # Drive the same system commands as caption buttons, acknowledging conhost's
                # UI thread as well as our tray thread before issuing the next transition.
                "def command(action):\n"
                "    result = ctypes.c_size_t()\n"
                "    assert user.SendMessageTimeoutW(hwnd, 0x112, action, 0, 2, 5000, ctypes.byref(result)), 'conhost system command timed out'\n"
                "def wait(test):\n"
                "    deadline = time.monotonic() + 5\n"
                "    while not test() and time.monotonic() < deadline: time.sleep(.02)\n"
                "    assert test(), f'native window state did not change: hidden={controller.hidden}, added={controller.added}, visible={user.IsWindowVisible(hwnd)}, minimized={user.IsIconic(hwnd)}, error={controller.error!r}'\n"
                "try:\n"
                "    command(0xF120)\n"  # SC_RESTORE
                "    wait(lambda: user.IsWindowVisible(hwnd) and not user.IsIconic(hwnd) and not user.IsZoomed(hwnd))\n"
                "    user.SetWindowPos(hwnd, None, 80, 90, 640, 360, 0x0014)\n"
                "    before = wintypes.RECT(); user.GetWindowRect(hwnd, ctypes.byref(before))\n"
                "    geometry = lambda rect: (rect.left, rect.top, rect.right, rect.bottom)\n"
                "    controller.start()\n"
                "    assert controller.owns_icon, 'the application icon was not loaded'\n"
                "    for maximized in (False, True):\n"
                "        if maximized:\n"
                "            command(0xF030)\n"  # SC_MAXIMIZE
                "            wait(lambda: user.IsZoomed(hwnd))\n"
                "        command(0xF020)\n"  # SC_MINIMIZE
                "        wait(lambda: controller.hidden and not user.IsWindowVisible(hwnd))\n"
                "        send(WM_TRAY, (1 << 16) | 0x405)\n"
                "        wait(lambda: not controller.hidden and not controller.added and user.IsWindowVisible(hwnd) and not user.IsIconic(hwnd))\n"
                "        assert bool(user.IsZoomed(hwnd)) == maximized, 'restore changed maximized state'\n"
                "        send(WM_TRAY, (1 << 16) | 0x405)\n"
                "        assert bool(user.IsZoomed(hwnd)) == maximized, 'duplicate restore changed maximized state'\n"
                "        if maximized:\n"
                "            command(0xF120)\n"
                "            wait(lambda: not user.IsZoomed(hwnd) and not user.IsIconic(hwnd))\n"
                "        after = wintypes.RECT(); user.GetWindowRect(hwnd, ctypes.byref(after))\n"
                "        assert geometry(before) == geometry(after), 'restore changed normal position/size'\n"
                "    command(0xF030)\n"
                "    wait(lambda: user.IsZoomed(hwnd))\n"
                "    command(0xF020)\n"
                "    wait(lambda: controller.hidden and not user.IsWindowVisible(hwnd))\n"
                # Simulate Shell losing the icon as well as sending its restart message.
                "    controller._remove_icon()\n"
                "    send(controller.restart_message)\n"
                "    wait(lambda: not controller.hidden and user.IsWindowVisible(hwnd) and not user.IsIconic(hwnd))\n"
                "    assert user.IsZoomed(hwnd) and not controller.added, 'Explorer recovery changed maximized state'\n"
                "    command(0xF020)\n"
                "    wait(lambda: controller.hidden and not user.IsWindowVisible(hwnd))\n"
                "    controller.close()\n"
                "    assert user.IsWindowVisible(hwnd), 'cleanup left terminal hidden'\n"
                "    assert not controller.thread.is_alive() and not controller.added\n"
                "    assert controller.notices == 4, 'expected one notification request per minimize'\n"
                "    controller = QuietTray(hwnd, 'PyApp quiet cleanup test', icon_path, lambda: None)\n"
                "    controller.start()\n"
                "    command(0xF020)\n"
                "    wait(lambda: controller.hidden and not user.IsWindowVisible(hwnd))\n"
                "    controller.close(activate=False)\n"
                "    assert user.IsWindowVisible(hwnd) and user.IsIconic(hwnd), 'quiet cleanup did not return window minimized'\n"
                "    assert not controller.thread.is_alive() and not controller.added\n"
                "    assert controller.notices == 1, 'quiet cleanup repeated a notification'\n"
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
            with subprocess.Popen(  # noqa: S603
                [conhost, python, str(script)], startupinfo=startup, creationflags=subprocess.CREATE_NEW_CONSOLE
            ) as child:
                try:
                    child.wait(timeout=25)
                finally:
                    if child.poll() is None:
                        child.kill()
            answer = result.read_text(encoding="utf-8")
            self.assertEqual(answer, "passed", answer)


if __name__ == "__main__":
    unittest.main()

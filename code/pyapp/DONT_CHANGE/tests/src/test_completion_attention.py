"""Taskbar outcome transitions and notification data, escaping, failures and completion routing."""

from __future__ import annotations

import base64
import ctypes
import io
import json
import os
import subprocess
import unittest
from types import SimpleNamespace
from typing import Protocol
from unittest import mock
from xml.etree import ElementTree as ET

from project_location import CODE

# isort: split

from pyapp.DONT_CHANGE.runtime import process_exit
from pyapp.DONT_CHANGE.scripts import config, console_tools
from pyapp.DONT_CHANGE.scripts import taskbar_status as taskbar
from pyapp.DONT_CHANGE.scripts import windows_notifications as notifications


def settings(**changes: object) -> SimpleNamespace:
    result = SimpleNamespace(
        **{
            "program_name": "Example {app}",
            "start_menu_shortcuts": True,
            "close_after_success": True,
            "close_after_failure": True,
            "close_after_keyboard_interrupt": True,
            "enable_crash_log": False,
            "play_sound_after_success": False,
            "play_sound_after_failure": False,
            "foreground_after_success": False,
            "foreground_after_failure": False,
            **changes,
        }
    )
    config.fill_missing_settings(result)
    result.MISSING_SETTINGS_FILLED_IN = []  # the assembled fixture now contains a complete settings file
    return result


class DwordReference(Protocol):
    """The DWORD buffer exposed by ctypes.byref() to the fake native callback."""

    _obj: ctypes.c_ulong


class TaskbarTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows native window handles")
    def test_foreground_uses_owned_hidden_wt_window_and_rejects_stale_handles(self):
        with mock.patch.dict(os.environ, {taskbar.WINDOW_ENV: "record"}), mock.patch.object(
            taskbar, "terminal_window", return_value=123
        ) as window, mock.patch.object(console_tools, "note_ignored"), mock.patch.object(
            taskbar.ctypes, "windll"
        ) as native, mock.patch.object(ctypes, "WinDLL", return_value=native.user32):
            native.user32.IsIconic.return_value = True
            console_tools.unminimize_terminal()
            console_tools.foreground_terminal()
            self.assertEqual(window.call_args_list, [mock.call(include_hidden=True)] * 2)
            self.assertEqual(native.user32.ShowWindow.call_args_list, [mock.call(123, 9)] * 2)
            native.user32.SetForegroundWindow.assert_called_once_with(123)
            native.user32.reset_mock()
            window.return_value = 0
            console_tools.unminimize_terminal()
            console_tools.foreground_terminal()
            native.user32.ShowWindow.assert_not_called()
            native.user32.SetForegroundWindow.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows native window handles")
    def test_completion_updates_activity_even_while_the_remembered_terminal_is_hidden(self):
        user = mock.Mock()
        user.IsWindow.return_value = True
        user.IsWindowVisible.return_value = False

        def owner(_hwnd: int, ptr: DwordReference) -> None:
            ptr._obj.value = 10

        def class_name(_hwnd: int, buffer: ctypes.Array[ctypes.c_wchar], _length: int) -> None:
            buffer.value = "ConsoleWindowClass"

        user.GetWindowThreadProcessId.side_effect = owner
        user.GetClassNameW.side_effect = class_name
        with mock.patch.object(taskbar.ctypes, "WinDLL", return_value=user), mock.patch.dict(
            os.environ, {taskbar.WINDOW_ENV: json.dumps({"hwnd": 123, "pid": 10}), taskbar.ACTIVITY_ENV: "1"}
        ), mock.patch.object(taskbar, "set_progress") as progress:
            taskbar.finish(settings(have_running_animation_in_taskbar=True), "success", stays_open=True)
            progress.assert_called_once_with(123, taskbar.TBPF_NOPROGRESS)
            self.assertNotIn(taskbar.ACTIVITY_ENV, os.environ)

    def test_running_animation_then_each_completion_policy(self):
        s = settings(
            have_running_animation_in_taskbar=True,
            highlight_on_success=True,
            highlight_on_failure=True,
            flash_on_success=True,
            flash_on_failure=True,
        )
        for outcome, state in (
            ("success", taskbar.TBPF_NORMAL),
            ("failure", taskbar.TBPF_ERROR),
            ("keyboard_interrupt", taskbar.TBPF_NOPROGRESS),
        ):
            with self.subTest(outcome=outcome), mock.patch.object(
                taskbar, "terminal_window", return_value=123
            ), mock.patch.object(taskbar, "set_progress") as progress, mock.patch.object(taskbar, "flash") as flash:
                taskbar.start(s)
                taskbar.finish(s, outcome, stays_open=True)
                self.assertEqual(
                    progress.call_args_list, [mock.call(123, taskbar.TBPF_INDETERMINATE), mock.call(123, state)]
                )
                self.assertEqual(flash.call_count, 0 if outcome == "keyboard_interrupt" else 1)

    def test_closing_clears_animation_instead_of_leaving_completion_attention(self):
        s = settings(have_running_animation_in_taskbar=True, highlight_on_failure=True, flash_on_failure=True)
        with mock.patch.object(taskbar, "terminal_window", return_value=123), mock.patch.object(
            taskbar, "set_progress"
        ) as progress, mock.patch.object(taskbar, "flash") as flash:
            taskbar.finish(s, "failure", stays_open=False)
            progress.assert_called_once_with(123, taskbar.TBPF_NOPROGRESS)
            flash.assert_not_called()

    def test_activity_clears_even_if_settings_changed_and_flash_survives_progress_failure(self):
        with mock.patch.dict(os.environ, {taskbar.ACTIVITY_ENV: "1"}), mock.patch.object(
            taskbar, "terminal_window", return_value=123
        ), mock.patch.object(taskbar, "set_progress") as progress:
            taskbar.finish(settings(), "keyboard_interrupt", False)
            progress.assert_called_once_with(123, taskbar.TBPF_NOPROGRESS)
            self.assertNotIn(taskbar.ACTIVITY_ENV, os.environ)
        with mock.patch.object(taskbar, "terminal_window", return_value=123), mock.patch.object(
            taskbar, "set_progress", side_effect=OSError("progress denied")
        ), mock.patch.object(taskbar, "note_ignored"), mock.patch.object(taskbar, "flash") as flash:
            taskbar.finish(settings(flash_on_failure=True), "failure", True)
            flash.assert_called_once_with(123)

    def test_defaults_no_window_and_denied_shell_do_not_interrupt_completion(self):
        with mock.patch.object(taskbar, "terminal_window") as window:
            taskbar.start(settings())
            taskbar.finish(settings(), "success", True)
            window.assert_not_called()
        with mock.patch.object(taskbar, "terminal_window", return_value=0), mock.patch.object(
            taskbar, "set_progress"
        ) as progress:
            taskbar.finish(settings(highlight_on_success=True), "success", True)
            progress.assert_not_called()
        with mock.patch.object(taskbar, "terminal_window", side_effect=OSError("shell unavailable")), mock.patch.object(
            taskbar, "note_ignored"
        ) as ignored:
            taskbar.finish(settings(highlight_on_success=True), "success", True)
            ignored.assert_called_once()


class NotificationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows PowerShell only")
    def test_xml_and_powershell_keep_untrusted_text_as_data(self):
        text = '<tag> & "quotes" \' apostrophe $(Get-Process) ä 日本 {braces}'
        with mock.patch.object(notifications.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            self.assertIsNone(notifications.show(text, text, "app-id"))
        args, kwargs = run.call_args
        command = args[0]
        self.assertEqual(base64.b64decode(command[-1]).decode("utf-16-le"), notifications.TOAST_SCRIPT)
        self.assertNotIn(text, " ".join(command))
        self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)
        # This is the escaped XML our own toast_xml() just generated, never an external document.
        xml = ET.fromstring(kwargs["env"]["PYAPP_TOAST_XML"])  # noqa: S314
        self.assertEqual([node.text for node in xml.findall("./visual/binding/text")], [text, text])
        audio = xml.find("audio")
        if audio is None:
            self.fail("The notification must suppress its own extra sound.")
        self.assertEqual(audio.attrib, {"silent": "true"})

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell only")
    def test_disabled_notifications_do_nothing_and_blocked_settings_are_reported(self):
        with mock.patch.object(notifications, "show") as show:
            notifications.complete(settings(), "success", "done", None, None)
            show.assert_not_called()
        with mock.patch.object(
            notifications.subprocess,
            "run",
            return_value=SimpleNamespace(
                returncode=2, stdout="Windows notification blocked: DisabledForUser", stderr=""
            ),
        ):
            problem = notifications.show("title", "message", "app-id")
            if problem is None:
                self.fail("Blocked notifications must return a problem.")
            self.assertIn("DisabledForUser", problem)
        with mock.patch.object(notifications, "show") as show, mock.patch.object(notifications, "print_warn") as warn:
            notifications.complete(
                settings(windows_notification_on_success=True, start_menu_shortcuts=False), "success", None, None, None
            )
            show.assert_not_called()
            self.assertIn("Start Menu", warn.call_args[0][0])

    def test_completion_formats_custom_text_even_when_closing_and_after_crash_log_is_written(self):
        s = settings(
            windows_notification_on_failure=True,
            windows_notification_title="Result: Example {app}",
            windows_notification_message_on_failure="{message} | {outcome} | {log_path} | {crash_log_path}",
        )
        with mock.patch.object(process_exit, "settings", return_value=s), mock.patch.object(
            process_exit, "print_report"
        ), mock.patch.object(process_exit, "write_crash_log", return_value="crash.txt"), mock.patch.object(
            process_exit, "print_crash_log_path"
        ), mock.patch.object(process_exit, "in_browser_terminal", return_value=False), mock.patch.object(
            notifications, "show", return_value=None
        ) as show, mock.patch.dict(os.environ, {"PYAPP_NOTIFICATION_APP_ID": "app-id"}), mock.patch.object(
            process_exit.sys, "stdout", io.StringIO()
        ):
            process_exit.complete("failure", "run.log", message="bad <input>")
        show.assert_called_once_with("Result: Example {app}", "bad <input> | failure | run.log | crash.txt", "app-id")

    def test_notification_failure_does_not_replace_the_original_report(self):
        with mock.patch.object(notifications, "show", side_effect=OSError("PowerShell denied")), mock.patch.object(
            notifications, "note_ignored"
        ), mock.patch.object(notifications, "print_warn") as warn:
            notifications.complete(
                settings(windows_notification_on_failure=True), "failure", "original error", None, None
            )
            self.assertIn("Windows notification failed", warn.call_args[0][0])


class CompletionSettingsTests(unittest.TestCase):
    def test_completion_focus_and_wait_policy_for_each_outcome_close_and_recovery_combination(self):
        # A hidden terminal is restored only by an explicit completion foreground request.
        for outcome in ("success", "failure", "keyboard_interrupt"):
            for close in (False, True):
                for foreground in (False, True):
                    for recovery in (False, True):
                        s = settings(
                            **{
                                "close_after_" + outcome: close,
                                "foreground_after_success": foreground,
                                "foreground_after_failure": foreground,
                            }
                        )
                        with self.subTest(
                            outcome=outcome, close=close, foreground=foreground, recovery=recovery
                        ), mock.patch.object(process_exit, "settings", return_value=s), mock.patch.object(
                            process_exit, "in_browser_terminal", return_value=False
                        ), mock.patch.object(process_exit, "set_terminal_title"), mock.patch.object(
                            process_exit, "set_terminal_icon"
                        ), mock.patch.object(process_exit, "set_terminal_colors"), mock.patch.object(
                            process_exit, "print_report"
                        ), mock.patch.object(process_exit, "write_crash_log", return_value=None), mock.patch.object(
                            process_exit, "unminimize_terminal"
                        ) as restore, mock.patch.object(
                            process_exit, "foreground_terminal"
                        ) as focus, mock.patch.object(process_exit, "wait_for_report") as wait, mock.patch.object(
                            taskbar, "finish"
                        ) as finish:
                            process_exit.complete(outcome, None, keep_open=recovery)
                            stays_open = not close or recovery
                            expected_focus = stays_open and foreground and outcome != "keyboard_interrupt"
                            self.assertEqual(restore.call_count, int(expected_focus))
                            self.assertEqual(focus.call_count, int(expected_focus))
                            self.assertEqual(wait.call_count, int(stays_open and not recovery))
                            finish.assert_called_once_with(s, outcome, stays_open)

    def test_custom_titles_and_sound_paths_are_used(self):
        s = settings(
            close_after_success=False,
            title_after_success="Done: Example {app}",
            play_sound_after_success=True,
            sound_after_success="sounds/custom.wav",
        )
        with mock.patch.object(process_exit, "settings", return_value=s), mock.patch.object(
            process_exit, "set_terminal_title"
        ) as title, mock.patch.object(process_exit, "set_terminal_icon"), mock.patch.object(
            process_exit, "print_report"
        ), mock.patch.object(process_exit, "wait_for_report"), mock.patch.object(process_exit, "play_sound") as sound:
            process_exit.complete("success", None)
        title.assert_called_once_with("Done: Example {app}")
        sound.assert_called_once_with(str(CODE / "pyapp" / "sounds" / "custom.wav"), wait=True)

    def test_empty_sound_disables_playback_even_when_switch_is_on(self):
        with mock.patch.object(
            process_exit, "settings", return_value=settings(play_sound_after_success=True, sound_after_success="")
        ), mock.patch.object(process_exit, "print_report"), mock.patch.object(process_exit, "play_sound") as sound:
            process_exit.complete("success", None)
            sound.assert_not_called()

    def test_runtime_fields_preserve_literal_braces_and_do_not_reformat_inserted_values(self):
        values = {
            "message": "bad {outcome} {program_name}",
            "outcome": "failure",
            "log_path": "run.log",
            "crash_log_path": "",
        }
        self.assertEqual(
            notifications.render_text("Example {app}: {message}", values), "Example {app}: bad {outcome} {program_name}"
        )
        self.assertEqual(
            notifications.render_text("literal {unknown} and {unfinished", values), "literal {unknown} and {unfinished"
        )

    def test_new_settings_are_validated_and_old_files_receive_defaults(self):
        for name, value in (
            ("highlight_on_failure", "yes"),
            ("flash_on_success", 1),
            ("allow_minimize", None),
            ("have_running_animation_in_taskbar", "yes"),
            ("windows_notification_on_failure", 1),
            ("sound_after_success", None),
            ("title_after_success", None),
            ("windows_notification_title", 5),
            ("windows_notification_message_on_failure", None),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(config.SettingsError, name):
                config.validate(settings(**{name: value}))
        old = settings()
        self.assertIs(old.have_running_animation_in_taskbar, False)
        self.assertEqual(old.sound_after_success, r"%WINDIR%\Media\notify.wav")
        self.assertEqual(old.title_after_failure, "[Failure] Example {app}")
        self.assertIs(old.allow_minimize, True)


if __name__ == "__main__":
    unittest.main()

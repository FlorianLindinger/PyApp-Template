"""Crash logs contain the app's prints; the raw output file is only kept after failures."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

import project_location  # also makes this checkout's code importable
from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.runtime import bg_watchdog, process_exit
from pyapp.DONT_CHANGE.runtime._pyapp import ExitMode
from pyapp.DONT_CHANGE.scripts.config import fill_missing_settings

SETTINGS = types.SimpleNamespace(
    enable_crash_log=True,
    crash_log_path="crash.txt",
    crash_log_path_is_relative_to_start_folder_if_relative=False,
    error_date_format="%Y",
)


class CrashLogTests(unittest.TestCase):
    def test_a_missing_cleanup_script_does_not_replace_the_crash_report(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(bg_watchdog, "note_ignored"), mock.patch.object(
            bg_watchdog.subprocess, "Popen"
        ) as create:
            s = types.SimpleNamespace(after_interpreter_crash_script=str(Path(folder) / "missing.py"))
            notice = bg_watchdog.launch_crash_cleanup(
                s, ExitMode.NO_REPORT, 0xC0000005, [sys.executable], {}, folder, "", Path(folder)
            )
            self.assertIn("could not start", notice)
            create.assert_not_called()

    def test_cleanup_only_starts_after_a_recognized_hard_crash_and_keeps_separate_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cleanup = root / "cleanup script.py"
            cleanup.write_text(
                "import os\nprint(os.environ['CRASH_EXIT_CODE'])\nprint(os.getcwd())\n", encoding="utf-8"
            )
            s = types.SimpleNamespace(
                after_interpreter_crash_script=str(cleanup), main_script_path=str(root / "main.py")
            )
            for mode, code in (
                (ExitMode.SUCCESS, 0xC0000005),
                (ExitMode.APP_EXIT, 0xC0000005),
                (ExitMode.NO_REPORT, 7),
                (ExitMode.NO_REPORT, 0xC000013A),
            ):
                with mock.patch.object(bg_watchdog.subprocess, "Popen") as create:
                    self.assertEqual(
                        bg_watchdog.launch_crash_cleanup(s, mode, code, [sys.executable], {}, folder, "", root), ""
                    )
                    create.assert_not_called()
            with mock.patch.object(bg_watchdog.threading, "Thread") as waiter:
                notice = bg_watchdog.launch_crash_cleanup(
                    s,
                    ExitMode.NO_REPORT,
                    0xC0000005,
                    [sys.executable],
                    dict(os.environ),
                    folder,
                    str(root / "app.log"),
                    root,
                )
                child = waiter.call_args.kwargs["target"].__self__
                self.assertEqual(child.wait(timeout=10), 0)
            self.assertIn("cleanup started", notice)
            output = (root / "app.recovery.log").read_text(encoding="utf-8")
            self.assertIn(str(0xC0000005), output)
            self.assertIn(folder, output)
            (root / paths.STOP_REQUEST_FILE_NAME).write_text("stop", encoding="utf-8")
            with mock.patch.object(bg_watchdog.subprocess, "Popen") as create:
                self.assertEqual(
                    bg_watchdog.launch_crash_cleanup(
                        s, ExitMode.NO_REPORT, 0xC0000005, [sys.executable], {}, folder, "", root
                    ),
                    "",
                )
                create.assert_not_called()

    def test_completion_prints_the_actual_unique_log_immediately_after_the_report(self):
        def print_traceback(_report: object) -> None:
            print("TRACEBACK")

        settings = types.SimpleNamespace(
            **vars(SETTINGS),
            close_after_failure=True,
            open_log_file_after_failure=False,
            open_crash_log_after_failure=False,
            play_sound_after_failure=False,
        )
        for enabled in (True, False):
            settings.enable_crash_log = enabled
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as folder:
                base = Path(folder, "crash report.txt")
                output = io.StringIO()
                with mock.patch.object(process_exit, "settings", return_value=settings), mock.patch.object(
                    process_exit, "get_log_path", return_value=str(base)
                ), mock.patch.object(process_exit, "in_browser_terminal", return_value=False), mock.patch.object(
                    process_exit, "print_report", side_effect=print_traceback
                ), mock.patch.object(sys, "stdout", output):
                    saved = process_exit.complete("failure", None, {"chain": []})
                if enabled:
                    self.assertIsNotNone(saved)
                    self.assertNotEqual(saved, str(base))
                    self.assertTrue(Path(saved or "").is_file())
                    self.assertEqual(output.getvalue(), f"TRACEBACK\nCrash log: {saved}\n")
                else:
                    self.assertIsNone(saved)
                    self.assertEqual(output.getvalue(), "TRACEBACK\n")

    def test_windows_terminal_link_encodes_spaces_but_displays_the_actual_path(self):
        output = mock.Mock()
        output.isatty.return_value = True
        path = Path("crash logs", "crash report_unique.txt").absolute()
        with mock.patch.dict(os.environ, {"WT_SESSION": "test"}), mock.patch.object(
            sys, "stdout", output
        ), mock.patch.object(process_exit, "enable_ansi"), mock.patch.object(
            process_exit, "in_browser_terminal", return_value=False
        ):
            process_exit.print_crash_log_path(str(path))
        text = "".join(call.args[0] for call in output.write.call_args_list)
        self.assertIn(f"\x1b]8;;{path.as_uri()}\x1b\\{path}\x1b]8;;\x1b\\", text)
        self.assertIn("%20", text)

    def write(self, folder: str, log_path: str):
        with mock.patch.object(process_exit, "settings", return_value=SETTINGS), mock.patch.object(
            process_exit, "get_log_path", return_value=str(Path(folder) / "crash.txt")
        ):
            path = process_exit.write_crash_log(None, "It failed.", log_path)
        if path is None:
            self.fail("no crash log was written")
        return Path(path).read_text(encoding="utf-8")

    def test_the_report_comes_first_then_everything_printed(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "log.txt"
            log.write_text("first print\nlast print\n", encoding="utf-8")
            text = self.write(folder, str(log))
        self.assertLess(text.index("It failed."), text.index("first print"))
        self.assertIn("last print", text)

    def test_without_a_log_the_report_is_still_written(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIn("It failed.", self.write(folder, ""))
            self.assertIn("It failed.", self.write(folder, str(Path(folder) / "missing.txt")))

    def test_a_crash_log_that_cannot_be_written_does_not_hide_the_report(self):
        settings = types.SimpleNamespace(
            **vars(SETTINGS),
            close_after_failure=True,
            open_log_file_after_failure=False,
            open_crash_log_after_failure=True,
            play_sound_after_failure=False,
        )
        report: Dict[str, object] = {"chain": []}
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder) / "a file"
            blocker.write_text("", encoding="utf-8")
            with mock.patch.object(process_exit, "settings", return_value=settings), mock.patch.object(
                process_exit, "get_log_path", return_value=str(blocker / "crash.txt")
            ), mock.patch.object(process_exit, "print_report") as print_report, mock.patch.object(
                process_exit, "print_error"
            ) as print_error, mock.patch.object(
                process_exit.os, "startfile", create=True
            ) as startfile, mock.patch.object(process_exit, "print_crash_log_path") as print_path:
                process_exit.complete("failure", None, report)
        print_report.assert_called_once_with(report)
        self.assertIn("Failed to write the crash log", print_error.call_args_list[-1][0][0])
        startfile.assert_not_called()
        print_path.assert_not_called()


class VariableExportTests(unittest.TestCase):
    def report(self):
        return {
            "plain": "ValueError: broken\n",
            "variables": [
                {
                    "exception_type": "ValueError",
                    "frames": [
                        {
                            "filename": "main.py",
                            "lineno": 12,
                            "name": "fail",
                            "locals": {"value": "7"},
                            "globals": {"global_value": "42"},
                        }
                    ],
                }
            ],
        }

    def test_enter_closes_without_exporting_values(self):
        with mock.patch.object(process_exit, "ask", return_value=""), mock.patch.object(
            process_exit, "save_and_open_variables"
        ) as export:
            process_exit.wait_for_report(self.report())
        export.assert_not_called()

    def test_v_appends_to_crash_log_once_and_opens_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder, "crash.txt")
            log.write_text("Original crash report", encoding="utf-8")
            report = self.report()
            with mock.patch.object(process_exit, "ask", side_effect=["v", "v", ""]), mock.patch.object(
                process_exit.os, "startfile"
            ) as open_file, mock.patch("builtins.print"):
                process_exit.wait_for_report(report, str(log))
            content = log.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("Original crash report"))
            self.assertEqual(content.count("Traceback variable snapshot"), 1)
            self.assertIn("global_value = 42", content)
            self.assertEqual(open_file.call_count, 2)

    def test_export_without_crash_logging_uses_a_separate_system_temp_file(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            process_exit.tempfile, "gettempdir", return_value=folder
        ), mock.patch.object(process_exit.os, "startfile"), mock.patch("builtins.print"):
            report = self.report()
            process_exit.save_and_open_variables(report)
            saved_path = report["variables_saved_path"]
            if not isinstance(saved_path, str):
                self.fail("the exported snapshot path must be text")
            exported = Path(saved_path)
            self.assertEqual(exported.parent, Path(folder))
            self.assertIn("value = 7", exported.read_text(encoding="utf-8"))

    def test_open_failure_does_not_lose_the_saved_snapshot(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
            process_exit.os, "startfile", side_effect=OSError("no editor")
        ), mock.patch.object(process_exit, "print_error") as error, mock.patch("builtins.print"):
            report = self.report()
            log = Path(folder, "crash.txt")
            process_exit.save_and_open_variables(report, str(log))
            self.assertTrue(log.is_file())
            self.assertIn("could not be opened", error.call_args[0][0])

    def test_report_without_python_frames_keeps_the_old_prompt(self):
        with mock.patch.object(process_exit, "wait_for_enter") as wait, mock.patch.object(process_exit, "ask") as ask:
            process_exit.wait_for_report({"variables": []})
        wait.assert_called_once()
        ask.assert_not_called()

    def test_missing_module_recovery_menu_can_export_before_quitting(self):
        report = self.report()
        with mock.patch.object(process_exit, "local_module_exists", return_value=False), mock.patch.object(
            process_exit, "ask", side_effect=["v", ""]
        ), mock.patch.object(process_exit, "save_and_open_variables") as export, mock.patch(
            "pyapp.DONT_CHANGE.scripts.env.venv.install_problem", return_value=None
        ), mock.patch(
            "pyapp.DONT_CHANGE.scripts.import_finder.distribution_for_import", return_value="example"
        ), mock.patch("builtins.print"):
            process_exit.handle_missing_module("example", "", False, report, "crash.txt")
        export.assert_called_once_with(report, "crash.txt")

    def test_write_failure_returns_to_the_prompt_without_hiding_the_error(self):
        with tempfile.TemporaryDirectory() as folder:
            blocker = Path(folder, "file")
            blocker.write_text("not a folder", encoding="utf-8")
            with mock.patch.object(process_exit, "print_error") as error, mock.patch.object(
                process_exit.os, "startfile"
            ) as open_file:
                process_exit.save_and_open_variables(self.report(), str(blocker / "variables.txt"))
            self.assertIn("Could not save", error.call_args[0][0])
            open_file.assert_not_called()


class CompletionForegroundTests(unittest.TestCase):
    def complete(
        self,
        outcome: str,
        enabled: bool,
        close: bool,
        browser: bool = False,
        keep_open: bool = False,
        fail: bool = False,
    ):
        s = types.SimpleNamespace(program_name="Example", open_crash_log_after_failure=False)
        fill_missing_settings(s)
        for name in ("success", "failure", "keyboard_interrupt"):
            setattr(s, "close_after_" + name, close)
            setattr(s, "open_log_file_after_" + name, False)
            setattr(s, "play_sound_after_" + name, False)
        for name in ("success", "failure"):
            setattr(s, "foreground_after_" + name, enabled if outcome in (name, "keyboard_interrupt") else False)
        with mock.patch.multiple(
            process_exit,
            settings=mock.Mock(return_value=s),
            in_browser_terminal=mock.Mock(return_value=browser),
            set_terminal_title=mock.DEFAULT,
            set_terminal_colors=mock.DEFAULT,
            set_terminal_icon=mock.DEFAULT,
            browser_terminal_ui=mock.DEFAULT,
            unminimize_terminal=mock.DEFAULT,
            foreground_terminal=mock.DEFAULT,
            print_report=mock.DEFAULT,
            write_crash_log=mock.Mock(return_value=None),
            wait_for_enter=mock.DEFAULT,
            note_ignored=mock.DEFAULT,
        ) as mocks:
            if fail:
                mocks["foreground_terminal"].side_effect = OSError("focus denied")
            process_exit.complete(outcome, None, keep_open=keep_open)
        return mocks

    def test_each_outcome_has_an_independent_opt_in(self):
        for outcome in ("success", "failure"):
            for enabled in (False, True):
                with self.subTest(outcome=outcome, enabled=enabled):
                    mocks = self.complete(outcome, enabled, False)
                    self.assertEqual(mocks["unminimize_terminal"].call_count, int(enabled))
                    self.assertEqual(mocks["foreground_terminal"].call_count, int(enabled))
                    mocks["browser_terminal_ui"].assert_not_called()
                    mocks["print_report"].assert_called_once()

    def test_keyboard_interrupt_does_not_use_success_or_failure_foreground_settings(self):
        for browser in (False, True):
            with self.subTest(browser=browser):
                mocks = self.complete("keyboard_interrupt", True, False, browser=browser)
                mocks["foreground_terminal"].assert_not_called()
                mocks["unminimize_terminal"].assert_not_called()
                mocks["browser_terminal_ui"].assert_not_called()
                mocks["print_report"].assert_called_once()
                mocks["wait_for_enter"].assert_called_once()

    def test_closing_window_does_not_flash_into_the_foreground(self):
        mocks = self.complete("success", True, True)
        mocks["foreground_terminal"].assert_not_called()
        mocks["wait_for_enter"].assert_not_called()

    def test_recovery_kept_open_can_request_attention(self):
        mocks = self.complete("failure", True, True, keep_open=True)
        mocks["foreground_terminal"].assert_called_once()
        mocks["wait_for_enter"].assert_not_called()

    def test_browser_uses_its_own_foreground_request(self):
        mocks = self.complete("failure", True, False, browser=True)
        mocks["browser_terminal_ui"].assert_called_once_with(foreground=True)
        mocks["foreground_terminal"].assert_not_called()

    def test_focus_failure_does_not_prevent_reporting_or_waiting(self):
        mocks = self.complete("failure", True, False, fail=True)
        mocks["note_ignored"].assert_called_once_with("foreground after failure")
        mocks["print_report"].assert_called_once()
        mocks["wait_for_enter"].assert_called_once()


class HiddenCompletionTests(unittest.TestCase):
    """After a successful run without a terminal, the completion handler runs in a hidden console."""

    def handle(self, returncodes: List[int]) -> List[Tuple[List[str], Dict[str, object]]]:
        calls: List[Tuple[List[str], Dict[str, object]]] = []

        def run(args: List[str], **kwargs: object) -> types.SimpleNamespace:
            calls.append((args, kwargs))
            return types.SimpleNamespace(returncode=returncodes[len(calls) - 1])

        settings = types.SimpleNamespace(close_after_success=True)
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(bg_watchdog.subprocess, "run", run):
            bg_watchdog.handle_exit(settings, ExitMode.SUCCESS, "app", False, "", "main.py", Path(folder))
        return calls

    def test_the_hidden_handler_can_never_wait_for_input(self):
        calls = self.handle([0])
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1]["stdin"], bg_watchdog.subprocess.DEVNULL)

    def test_a_failing_hidden_handler_is_shown_in_a_window(self):
        calls = self.handle([1, 0])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][0][0], bg_watchdog.paths.CONHOST_EXE)

    def test_the_handler_ends_when_its_prompt_cannot_be_answered(self):
        with tempfile.TemporaryDirectory() as folder:
            # Test subprocesses execute fixed fixture/helper code using the local interpreter or Git.
            completed = subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(project_location.DONT_CHANGE / "runtime" / "process_exit.py"),
                    *("99", "", "true", "", "main.py"),  # an exit mode the handler does not know: it fails
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                env={**os.environ, "PYAPP_RUN_DIR": folder},
                timeout=60,
                check=False,
            )
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn("Unknown exit mode 99", completed.stdout)


class RawOutputTests(unittest.TestCase):
    """The raw output stays in the run folder while the app runs; only a failure's is kept by the log."""

    def outcome(self, mode: int, content: str = "raw") -> Tuple[bool, bool]:
        """(still in the run folder, now next to the log) after the app ended with mode."""
        with tempfile.TemporaryDirectory() as folder:
            run_dir = Path(folder) / "run"
            run_dir.mkdir()
            log = str(Path(folder) / "log.txt")
            raw = run_dir / paths.RAW_OUTPUT_FILE_NAME
            raw.write_text(content, encoding="utf-8")
            bg_watchdog.keep_raw_output(str(raw), log, mode, run_dir)
            kept = Path(log + bg_watchdog.OUTPUT_LOG_SUFFIX)
            if kept.exists():
                self.assertEqual(kept.read_text(encoding="utf-8"), content)
            return raw.exists(), kept.exists()

    def test_removed_after_a_normal_end(self):
        self.assertEqual(self.outcome(ExitMode.SUCCESS), (False, False))

    def test_moved_next_to_the_log_after_failures(self):
        for mode in (ExitMode.NO_REPORT, ExitMode.APP_EXIT, ExitMode.WRAPPER_ERROR, ExitMode.WATCHDOG_ERROR):
            with self.subTest(mode=mode):
                self.assertEqual(self.outcome(mode), (False, True))

    def test_an_empty_one_is_removed_after_any_end(self):
        """Ctrl+C, a closed window or an error left an empty twin next to nearly every log."""
        for mode in (ExitMode.SUCCESS, ExitMode.NO_REPORT, ExitMode.APP_EXIT, ExitMode.WATCHDOG_ERROR):
            with self.subTest(mode=mode):
                self.assertEqual(self.outcome(mode, content=""), (False, False))

    def test_a_missing_one_is_no_error(self):
        with tempfile.TemporaryDirectory() as folder:
            bg_watchdog.keep_raw_output(str(Path(folder) / "none"), str(Path(folder) / "log.txt"), 0, Path(folder))
            bg_watchdog.keep_raw_output("", "", 0, Path(folder))

    def test_output_from_before_the_wrapper_started_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder) / paths.RAW_OUTPUT_FILE_NAME
            bg_watchdog.save_early_output(str(raw), b"Fatal Python error")
            self.assertEqual(raw.read_bytes(), b"Fatal Python error")
            # The wrapper's own capture is never replaced.
            bg_watchdog.save_early_output(str(raw), b"pipe copy")
            self.assertEqual(raw.read_bytes(), b"Fatal Python error")
            bg_watchdog.save_early_output("", b"no log")


if __name__ == "__main__":
    unittest.main()

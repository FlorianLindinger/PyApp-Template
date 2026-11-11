"""Crash logs contain the app's prints; the raw output file is only kept after failures."""

from __future__ import annotations

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
from pyapp.DONT_CHANGE.runtime import bg_watchdog, process_exit
from pyapp.DONT_CHANGE.runtime._pyapp import ExitMode

SETTINGS = types.SimpleNamespace(
    enable_crash_log=True,
    crash_log_path="crash.txt",
    crash_log_path_is_relative_to_start_folder_if_relative=False,
    error_date_format="%Y",
)


class CrashLogTests(unittest.TestCase):
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
            ) as print_error, mock.patch.object(process_exit.os, "startfile", create=True) as startfile:
                process_exit.complete("failure", None, report)
        print_report.assert_called_once_with(report)
        self.assertIn("Failed to write the crash log", print_error.call_args_list[-1][0][0])
        startfile.assert_not_called()


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


class WindowsTerminalTests(unittest.TestCase):
    def test_semicolons_do_not_split_the_wt_command_line(self):
        from pyapp.DONT_CHANGE.actions.start_program import wt_command

        command = wt_command("A; B", "#3B78FF", ["python.exe", "C:\\R;D\\watchdog.py"])
        self.assertEqual(
            command,
            ["wt.exe", "--title", "A\\; B", "--tabColor", "#3B78FF", "python.exe", "C:\\R\\;D\\watchdog.py"],
        )
        self.assertEqual(wt_command("App", None, ["x"]), ["wt.exe", "--title", "App", "x"])


class RawOutputTests(unittest.TestCase):
    def remaining_after(self, mode: int) -> bool:
        with tempfile.TemporaryDirectory() as folder:
            log = str(Path(folder) / "log.txt")
            raw = Path(log + bg_watchdog.OUTPUT_LOG_SUFFIX)
            raw.write_text("raw", encoding="utf-8")
            bg_watchdog.remove_raw_output_after_success(log, mode, Path(folder))
            return raw.exists()

    def test_removed_after_a_normal_end(self):
        self.assertFalse(self.remaining_after(ExitMode.SUCCESS))

    def test_kept_after_failures(self):
        for mode in (ExitMode.NO_REPORT, ExitMode.APP_EXIT, ExitMode.WRAPPER_ERROR, ExitMode.WATCHDOG_ERROR):
            with self.subTest(mode=mode):
                self.assertTrue(self.remaining_after(mode))

    def test_output_from_before_the_wrapper_started_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            log = str(Path(folder) / "log.txt")
            raw = Path(log + bg_watchdog.OUTPUT_LOG_SUFFIX)
            bg_watchdog.save_early_output(log, b"Fatal Python error")
            self.assertEqual(raw.read_bytes(), b"Fatal Python error")
            # The wrapper's own capture is never replaced.
            bg_watchdog.save_early_output(log, b"pipe copy")
            self.assertEqual(raw.read_bytes(), b"Fatal Python error")
            bg_watchdog.save_early_output("", b"no log")


if __name__ == "__main__":
    unittest.main()

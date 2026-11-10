"""Crash logs contain the app's prints; the raw output file is only kept after failures."""

from __future__ import annotations

import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import project_location  # noqa: F401 - make this checkout's code importable
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

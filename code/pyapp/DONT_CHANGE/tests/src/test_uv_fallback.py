"""Installing a Python with a uv that is too old: one retry with a newer uv, only when it can help."""

from __future__ import annotations

import unittest
from typing import List, Optional
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "pyapp" importable

# isort: split

from pyapp.DONT_CHANGE.scripts.env import pythons
from pyapp.DONT_CHANGE.scripts.errors import SetupError


class InstallPythonTests(unittest.TestCase):
    def install(self, exit_codes: List[int], newer_uv: bool, offered: Optional[bool] = False):
        with mock.patch.object(pythons, "run_uv", side_effect=exit_codes) as run_uv, mock.patch.object(
            pythons, "python_offered", return_value=offered
        ), mock.patch.object(pythons, "install_newer_uv", return_value=newer_uv) as install_newer_uv, mock.patch.object(
            pythons, "invalidate_runtime_cache"
        ), mock.patch.object(pythons, "find_python", return_value="python.exe"), mock.patch.object(
            pythons, "show_setup_window"
        ), mock.patch.object(pythons, "available_summary", return_value=""), mock.patch.object(pythons, "settings"):
            try:
                return pythons.install_python("3.99"), run_uv.call_count, install_newer_uv.call_count
            except SetupError:
                return None, run_uv.call_count, install_newer_uv.call_count

    def test_a_python_that_does_not_start_gives_a_message(self):
        import subprocess

        for error in (OSError(1260, "blocked by group policy"), subprocess.TimeoutExpired("python", 30)):
            with self.subTest(error=type(error).__name__), mock.patch.object(
                pythons.subprocess, "check_output", side_effect=error
            ), self.assertRaises(SetupError) as raised:
                pythons.interpreter_version("C:\\x\\python.exe")
            self.assertIn("C:\\x\\python.exe", str(raised.exception))

    def test_first_try_needs_no_newer_uv(self):
        self.assertEqual(self.install([0], True), ("python.exe", 1, 0))

    def test_retries_with_a_newer_uv(self):
        self.assertEqual(self.install([1, 0], True), ("python.exe", 2, 1))

    def test_error_when_the_newer_uv_also_fails(self):
        self.assertEqual(self.install([1, 1], True), (None, 2, 1))

    def test_error_without_a_newer_uv(self):
        self.assertEqual(self.install([1], False), (None, 1, 1))

    def test_no_newer_uv_when_this_uv_knows_the_python(self):
        # The download failed (offline, proxy); another uv would fail the same way.
        self.assertEqual(self.install([1], True, offered=True), (None, 1, 0))

    def test_an_unclear_answer_keeps_the_retry(self):
        self.assertEqual(self.install([1, 0], True, offered=None), ("python.exe", 2, 1))

    def test_uv_decides_whether_it_offers_a_request(self):
        for exit_code, output, expected in (
            (0, '[{"version": "3.12.4"}]', True),
            (0, "[]", False),
            (2, "", None),  # an older uv that does not accept a request here
            (0, "not json", None),
            (0, "{}", None),
        ):
            with self.subTest(output=output), mock.patch.object(
                pythons, "run_uv_captured", return_value=(exit_code, output, "")
            ) as run:
                self.assertIs(pythons.python_offered("3.12-3.14"), expected)
                self.assertIn(">=3.12,<3.15", run.call_args[0][0])


if __name__ == "__main__":
    unittest.main()

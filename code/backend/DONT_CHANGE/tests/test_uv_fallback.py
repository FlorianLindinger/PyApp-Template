"""Installing a Python with a uv that is too old: one retry with a newer uv."""

from __future__ import annotations

import unittest
from typing import List
from unittest import mock

from project_location import CODE  # noqa: F401 - makes "backend" importable

# isort: split

from backend.DONT_CHANGE.scripts.env import pythons
from backend.DONT_CHANGE.scripts.errors import SetupError


class InstallPythonTests(unittest.TestCase):
    def install(self, exit_codes: List[int], newer_uv: bool):
        with mock.patch.object(pythons, "run_uv", side_effect=exit_codes) as run_uv, mock.patch.object(
            pythons, "install_newer_uv", return_value=newer_uv
        ) as install_newer_uv, mock.patch.object(pythons, "invalidate_runtime_cache"), mock.patch.object(
            pythons, "find_python", return_value="python.exe"
        ), mock.patch.object(pythons, "show_setup_window"), mock.patch.object(
            pythons, "available_summary", return_value=""
        ), mock.patch.object(pythons, "settings"):
            try:
                return pythons.install_python("3.99"), run_uv.call_count, install_newer_uv.call_count
            except SetupError:
                return None, run_uv.call_count, install_newer_uv.call_count

    def test_first_try_needs_no_newer_uv(self):
        self.assertEqual(self.install([0], True), ("python.exe", 1, 0))

    def test_retries_with_a_newer_uv(self):
        self.assertEqual(self.install([1, 0], True), ("python.exe", 2, 1))

    def test_error_when_the_newer_uv_also_fails(self):
        self.assertEqual(self.install([1, 1], True), (None, 2, 1))

    def test_error_without_a_newer_uv(self):
        self.assertEqual(self.install([1], False), (None, 1, 1))


if __name__ == "__main__":
    unittest.main()

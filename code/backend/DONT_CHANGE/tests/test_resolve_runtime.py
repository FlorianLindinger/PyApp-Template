"""bootstrap/resolve_runtime.py: settings, version rules, and messages for company PCs."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "bootstrap"), *sys.path]):
    import resolve_runtime as tool


class SettingsTests(unittest.TestCase):
    def test_plain_literals_are_read_and_the_last_one_wins(self):
        text = 'uv_cache = "global"\nuv_cache = "local"  # note\nflag: bool = True\nnothing = None\n'
        self.assertEqual(tool.read_settings(text), {"uv_cache": "local", "flag": True, "nothing": None})

    def test_expressions_count_as_missing(self):
        self.assertEqual(tool.read_settings('uv_cache = "a"\nuv_cache = "a" + "b"\nname = f(1)\n'), {"uv_cache": "a"})

    def test_empty_text_values_stay_empty(self):
        self.assertEqual(tool.read_settings('python_version = ""  # newest\n'), {"python_version": ""})

    def test_indented_lines_are_ignored(self):
        self.assertEqual(tool.read_settings('    uv_cache = "local"\n'), {})


class VersionTests(unittest.TestCase):
    def test_rules(self):
        for version, spec, expected in (
            ("0.11.32", "", True),
            ("0.11.32", "0.11.32", True),
            ("0.11.32", "==0.11.31", False),
            ("0.11.0", "0.11", True),
            ("0.11.32", ">=0.9,<1", True),
            ("1.2.0", ">=0.9,<1", False),
            ("0.11.32", "~=0.11", True),
            ("1.0.0", "~=0.11", False),
            ("0.11.32", "!=0.11.32", False),
        ):
            with self.subTest(version=version, spec=spec):
                self.assertEqual(tool.version_satisfies(version, spec), expected)

    def test_a_clause_that_makes_no_sense_is_reported(self):
        with self.assertRaises(tool.BootstrapError):
            tool.version_satisfies("1.0.0", "about 1")

    def test_exact_versions(self):
        self.assertEqual(tool.exact_version("0.11.32"), "0.11.32")
        self.assertEqual(tool.exact_version("==0.11.32"), "0.11.32")
        self.assertIsNone(tool.exact_version(">=0.11.32"))
        self.assertIsNone(tool.exact_version(""))


class CompanyPcTests(unittest.TestCase):
    def test_a_refused_program_is_explained(self):
        error = OSError()
        error.winerror = 1260  # blocked by group policy
        message = tool.explain_start_failure("uv.exe", error)
        self.assertIn("company policy", message)
        self.assertIn('python_source = "system"', message)

    def test_other_start_failures_are_not_blamed_on_a_policy(self):
        self.assertNotIn("policy", tool.explain_start_failure("uv.exe", OSError("broken")))

    def test_a_program_that_cannot_start_is_remembered(self):
        error = OSError()
        error.winerror = 1260
        with mock.patch.object(tool.subprocess, "run", side_effect=error), mock.patch.object(
            tool, "_start_problems", new=list[str]()
        ):
            self.assertIsNone(tool.uv_version_of("uv.exe"))
            self.assertIn("company policy", tool._start_problems[0])

    def test_system_python_downloads_nothing(self):
        with mock.patch.dict(os.environ, {"UV_MANAGED_PYTHON": "1"}):
            tool.set_uv_environment({}, "system")
            self.assertEqual(os.environ["UV_PYTHON_PREFERENCE"], "only-system")
            self.assertEqual(os.environ["UV_PYTHON_DOWNLOADS"], "never")
            self.assertNotIn("UV_MANAGED_PYTHON", os.environ)

    def test_no_dialog_when_the_window_is_visible(self):
        with mock.patch.dict(os.environ, {"PYAPP_ENTRYPOINT_NO_PAUSE": "1"}), mock.patch("ctypes.windll") as windll:
            tool.show_failure_dialog("x")
            windll.user32.MessageBoxW.assert_not_called()

    def test_a_blocked_download_says_what_to_do(self):
        refused = tool.urllib.error.URLError("refused")
        with mock.patch.object(tool.urllib.request, "urlopen", side_effect=refused), self.assertRaises(
            tool.BootstrapError
        ) as raised:
            tool.download("https://github.com/x", DONT_CHANGE / "tmp" / "never-written")
        self.assertIn("firewall", str(raised.exception))
        self.assertIn("make_portable", str(raised.exception))


class CacheTests(unittest.TestCase):
    def test_batch_special_characters_are_kept(self):
        text = tool.cache_text("C:\\a%b\\uv.exe", "C:\\p.exe", "s")
        self.assertIn('set "PYAPP_UV=C:\\a%%b\\uv.exe"', text)
        self.assertTrue(text.startswith("rem ascii\r\n"))

    def test_non_ascii_paths_are_marked(self):
        self.assertTrue(tool.cache_text("C:\\Müller\\uv.exe", "p", "s").startswith("rem utf-8"))


if __name__ == "__main__":
    unittest.main()

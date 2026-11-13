"""The verifier prints warnings and preserves failing check results."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from typing import List
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import verify_launcher


class VerifyLauncherTests(unittest.TestCase):
    def test_check_reports_warning_for_diagnostics(self):
        output = io.StringIO()
        with mock.patch.object(verify_launcher.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess(["ruff"], 1)
            self.assertFalse(verify_launcher.run_check("Ruff lint", ["ruff", "check", "."]))
        run.assert_called_once_with(["ruff", "check", "."], cwd=DONT_CHANGE, check=False)
        self.assertIn("Ruff lint reported problems", output.getvalue())

    def test_check_reports_tool_error_separately(self):
        output = io.StringIO()
        with mock.patch.object(verify_launcher.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess(["ruff"], 2)
            self.assertFalse(verify_launcher.run_check("Ruff lint", ["ruff"]))
        self.assertIn("Ruff lint could not complete (exit code 2)", output.getvalue())
        self.assertNotIn("reported problems", output.getvalue())

    def test_success_does_not_print_a_warning(self):
        output = io.StringIO()
        with mock.patch.object(verify_launcher.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess(["ruff"], 0)
            self.assertTrue(verify_launcher.run_check("Ruff lint", ["ruff"]))
        self.assertNotIn("reported problems", output.getvalue())
        self.assertNotIn("could not complete", output.getvalue())

    def test_main_runs_remaining_checks_after_a_warning(self):
        def command_for(name: str) -> List[str]:
            return [name]

        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(sys, "argv", ["verify_launcher.py"]))
            stack.enter_context(mock.patch.object(verify_launcher, "tool_command", side_effect=command_for))
            run = stack.enter_context(mock.patch.object(verify_launcher.subprocess, "run"))
            stack.enter_context(contextlib.redirect_stdout(output))
            run.side_effect = [subprocess.CompletedProcess([], code) for code in (1, 0, 0)]
            self.assertEqual(verify_launcher.main(), 1)
        self.assertEqual(run.call_count, 3)
        self.assertIn(str(DONT_CHANGE / "ruff.toml"), output.getvalue())
        self.assertIn("Ruff lint reported problems", output.getvalue())
        self.assertIn("The launcher failed verification.", output.getvalue())


class ToolVersionTests(unittest.TestCase):
    def command(self, version: str, uvx: bool = True) -> List[str]:
        def which(name: str) -> object:
            return {"ruff": "C:\\bin\\ruff.exe", "uvx": "C:\\bin\\uvx.exe" if uvx else None}.get(name)

        with mock.patch.object(verify_launcher.shutil, "which", side_effect=which), mock.patch.object(
            verify_launcher.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, f"ruff {version}\n", "")
        ):
            return verify_launcher.tool_command("ruff")

    def test_a_new_enough_tool_on_path_is_used(self):
        self.assertEqual(self.command("0.17.4"), ["C:\\bin\\ruff.exe"])

    def test_an_older_tool_is_replaced_by_a_new_enough_one_through_uvx(self):
        self.assertEqual(self.command("0.16.10"), ["C:\\bin\\uvx.exe", "--from", "ruff>=0.17.0", "ruff"])

    def test_an_older_tool_without_uvx_is_an_error_that_names_the_minimum(self):
        with self.assertRaises(FileNotFoundError) as raised:
            self.command("0.16.10", uvx=False)
        self.assertIn("0.17.0 or newer", str(raised.exception))


class ToolRunTests(unittest.TestCase):
    def outcome(self, problem: BaseException):
        def main() -> int:
            raise problem

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            return verify_launcher._ui.run(main), output.getvalue()

    def test_expected_problems_are_a_short_message(self):
        code, text = self.outcome(TimeoutError("too slow"))
        self.assertEqual(code, 1)
        self.assertIn("too slow", text)

    def test_ctrl_c_is_reported(self):
        self.assertEqual(self.outcome(KeyboardInterrupt())[0], 130)

    def test_programming_errors_keep_their_traceback(self):
        with self.assertRaises(KeyError):
            self.outcome(KeyError("bug"))


if __name__ == "__main__":
    unittest.main()

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

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "scripts" / "tools"), *sys.path]):
    import verify_launcher


class VerifyLauncherTests(unittest.TestCase):
    def test_check_reports_warning_for_diagnostics(self):
        output = io.StringIO()
        with mock.patch.object(verify_launcher.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess(["ruff"], 1)
            self.assertFalse(verify_launcher.run_check("Ruff lint", ["ruff", "check", "."]))
        run.assert_called_once_with(["ruff", "check", "."], cwd=DONT_CHANGE, check=False)
        self.assertIn("[Warning] Ruff lint reported problems", output.getvalue())

    def test_check_reports_tool_error_separately(self):
        output = io.StringIO()
        with mock.patch.object(verify_launcher.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess(["ruff"], 2)
            self.assertFalse(verify_launcher.run_check("Ruff lint", ["ruff"]))
        self.assertIn("[Error] Ruff lint could not complete (exit code 2)", output.getvalue())
        self.assertNotIn("[Warning]", output.getvalue())

    def test_success_does_not_print_a_warning(self):
        output = io.StringIO()
        with mock.patch.object(verify_launcher.subprocess, "run") as run, contextlib.redirect_stdout(output):
            run.return_value = subprocess.CompletedProcess(["ruff"], 0)
            self.assertTrue(verify_launcher.run_check("Ruff lint", ["ruff"]))
        self.assertNotIn("[Warning]", output.getvalue())
        self.assertNotIn("[Error]", output.getvalue())

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
        self.assertIn("[Warning] Ruff lint", output.getvalue())
        self.assertIn("[Error] The launcher failed verification.", output.getvalue())


if __name__ == "__main__":
    unittest.main()

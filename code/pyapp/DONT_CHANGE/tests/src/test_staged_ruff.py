"""pyapp_tools/check_staged_ruff (git_hooks/pre-commit): Ruff on the staged launcher files."""

from __future__ import annotations

import io
import os
import sys
import unittest
from typing import List, Tuple
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import _paths  # noqa: F401 - imported by the tool; the tools folder is only on sys.path here
    import check_staged_ruff as tool

PREFIX = "code/pyapp/DONT_CHANGE/"


@mock.patch.dict(os.environ, {"NO_COLOR": "1"})
class StagedRuffTests(unittest.TestCase):
    def test_lint_diagnostics_include_the_actual_staged_source_line(self):
        diagnostic = PREFIX + "a.py:2:8: F401 unused import"
        with mock.patch.object(tool, "run_ruff", side_effect=[(1, diagnostic), (0, "")]):
            self.assertEqual(
                tool.problems_in(["ruff"], PREFIX + "a.py", b"# staged version\nimport os\n"),
                # The link opens the line from VS Code's "Show Command Output", where the path is only text.
                [
                    diagnostic
                    + "\n    | import os\n    "
                    + (tool.PROJECT_ROOT / PREFIX / "a.py").resolve().as_uri()
                    + "#L2"
                ],
            )

    def test_a_secret_in_a_lint_source_line_is_masked(self):
        secret = "gh" + "p_" + "a1B2" * 10
        diagnostic = PREFIX + "a.py:1:1: F821 undefined name"
        with mock.patch.object(tool, "run_ruff", side_effect=[(1, diagnostic), (0, "")]):
            problems = tool.problems_in(["ruff"], PREFIX + "a.py", f'unknown("{secret}")\n'.encode())
        self.assertIn('    | unknown("ghp_****")', problems[0])
        self.assertNotIn(secret, problems[0])

    def test_popup_starts_with_the_first_diagnostic(self):
        output = io.StringIO()
        diagnostic = PREFIX + "a.py:12:3: F401 unused import"
        with mock.patch.object(tool, "staged_python_files", return_value=[PREFIX + "a.py"]), mock.patch.object(
            tool, "git", return_value=b"import os\n"
        ), mock.patch.object(tool, "problems_in", return_value=[diagnostic]), mock.patch("sys.stdout", output):
            self.assertEqual(tool.main(["ruff"]), 1)
        self.assertEqual(
            output.getvalue().splitlines()[0],
            "Commit blocked: Ruff: "
            + diagnostic
            + '. Fix and stage the reported code. Click "Show Command Output" for details.',
        )
        self.assertIn("Review and stage the corrected files", output.getvalue())

    def test_format_only_popup_is_short_and_details_list_every_file(self):
        names = [PREFIX + "a.py", PREFIX + "b.py", PREFIX + "c.py"]
        output = io.StringIO()
        with mock.patch.object(tool, "staged_python_files", return_value=names), mock.patch.object(
            tool, "git", return_value=b"x=1\n"
        ), mock.patch.object(tool, "run_ruff", side_effect=[(0, ""), (1, "")] * 3), mock.patch("sys.stdout", output):
            self.assertEqual(tool.main(["ruff"]), 1)
        text = output.getvalue()
        first = text.splitlines()[0]  # the one line Git clients show
        for key in ("Commit blocked", "3 staged Python files", "verify_launcher.bat --fix"):
            self.assertIn(key, first)
        for name in names:
            self.assertIn(name + ": not formatted", text)
        # The repair command is available both in the popup and alongside the detailed steps.
        self.assertEqual(text.count("verify_launcher.bat --fix"), 2)
        self.assertIn("1. Format the files above.", text)
        self.assertIn("2. Review and stage the corrected files.", text)
        self.assertIn("3. Commit again.", text)
        self.assertIn("This check does not change files or staging.", text)

    def test_single_formatting_problem_uses_singular_wording(self):
        output = io.StringIO()
        with mock.patch.object(tool, "staged_python_files", return_value=[PREFIX + "a.py"]), mock.patch.object(
            tool, "git", return_value=b"x=1\n"
        ), mock.patch.object(tool, "run_ruff", side_effect=[(0, ""), (1, "")]), mock.patch("sys.stdout", output):
            self.assertEqual(tool.main(["ruff"]), 1)
        self.assertIn("1 staged Python file needs formatting.", output.getvalue().splitlines()[0])

    def test_lint_location_takes_priority_over_formatting_in_the_popup(self):
        diagnostic = PREFIX + "b.py:12:3: F401 unused import"
        output = io.StringIO()
        with mock.patch.object(tool, "staged_python_files", return_value=[PREFIX + "a.py"]), mock.patch.object(
            tool, "git", return_value=b""
        ), mock.patch.object(
            tool, "problems_in", return_value=[PREFIX + "a.py: not formatted", diagnostic]
        ), mock.patch("sys.stdout", output):
            self.assertEqual(tool.main(["ruff"]), 1)
        self.assertIn(diagnostic, output.getvalue().splitlines()[0])

    def test_formatter_failure_without_output_has_a_useful_message(self):
        with mock.patch.object(tool, "run_ruff", side_effect=[(0, ""), (2, "")]):
            self.assertEqual(
                tool.problems_in(["ruff"], PREFIX + "a.py", b""),
                [PREFIX + "a.py: Ruff format could not complete (exit code 2)"],
            )

    def test_formatter_details_are_kept_with_secrets_masked(self):
        secret = "gh" + "p_" + "a1B2" * 10
        diff = f'@@ -1 +1 @@\n-token="{secret}"\n+token = "{secret}"'
        with mock.patch.object(tool, "run_ruff", side_effect=[(0, ""), (1, diff)]):
            problems = tool.problems_in(["ruff"], PREFIX + "a.py", b"")
        self.assertIn("@@ -1 +1 @@", problems[0])
        self.assertIn('+token = "ghp_****"', problems[0])
        self.assertNotIn(secret, problems[0])

    def run_main(self, names: List[str], lint: int = 0, form: int = 0) -> Tuple[int, List[List[str]]]:
        """main() with fake staged files and a fake Ruff; returns (exit code, Ruff calls)."""
        calls: List[List[str]] = []

        def fake_ruff(ruff: List[str], arguments: List[str], name: str, content: bytes) -> Tuple[int, str]:
            calls.append([arguments[0], name])
            return (lint, f"{name}:1:1: F401 unused") if arguments[0] == "check" else (form, "")

        def fake_git(*arguments: str) -> bytes:
            if arguments[0] == "diff":
                return "\0".join(names).encode("utf-8")
            return b"import os\n"  # git show :<file>

        with mock.patch.object(tool, "git", side_effect=fake_git), mock.patch.object(
            tool, "run_ruff", side_effect=fake_ruff
        ), mock.patch("builtins.print"):
            return tool.main(["ruff"]), calls

    def test_clean_staged_files_pass(self):
        code, calls = self.run_main([PREFIX + "scripts/a.py"])
        self.assertEqual(code, 0)
        self.assertEqual(calls, [["check", PREFIX + "scripts/a.py"], ["format", PREFIX + "scripts/a.py"]])

    def test_lint_problems_and_unformatted_code_stop_the_commit(self):
        self.assertEqual(self.run_main([PREFIX + "a.py"], lint=1)[0], 1)
        self.assertEqual(self.run_main([PREFIX + "a.py"], form=1)[0], 1)

    def test_only_launcher_python_files_are_checked(self):
        code, calls = self.run_main(["code/main.py", PREFIX + "README.md", "README.md"])
        self.assertEqual((code, calls), (0, []))

    def test_a_missing_ruff_does_not_stop_the_commit(self):
        with mock.patch.object(tool, "staged_python_files", return_value=[PREFIX + "a.py"]), mock.patch.object(
            tool, "tool_command", side_effect=FileNotFoundError("no ruff")
        ), mock.patch("builtins.print"):
            self.assertEqual(tool.main(), 0)

    def test_the_staged_content_is_what_ruff_reads(self):
        with mock.patch.object(tool.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout=b"", stderr=b"")
            tool.run_ruff(["ruff"], ["check"], PREFIX + "a.py", b"staged text")
        command = run.call_args[0][0]
        self.assertEqual(command[-3:], ["--stdin-filename", PREFIX + "a.py", "-"])
        self.assertEqual(run.call_args[1]["input"], b"staged text")


if __name__ == "__main__":
    unittest.main()

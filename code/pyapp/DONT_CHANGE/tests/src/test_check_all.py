"""pyapp_tools/check_all (and git_hooks/pre-push): every check at once, with a summary."""

from __future__ import annotations

import io
import re
import sys
import unittest
from typing import Dict, List, Tuple
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import _paths  # noqa: F401 - imported by the tool; the tools folder is only on sys.path here
    import check_all as tool


class CheckAllTests(unittest.TestCase):
    def test_windows_child_line_endings_are_normalized_before_printing(self):
        output = io.StringIO()
        with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
            run.return_value = mock.Mock(returncode=1, stdout=b"Heading\r\nfixture.py:12:3: broken\r\n")
            self.assertEqual(tool.run_step(tool.STEPS[2], "", hook=True), 1)
        self.assertNotIn("\r", output.getvalue())
        self.assertIn("Heading\nfixture.py:12:3: broken\n", output.getvalue())

    def test_real_child_output_is_buffered_behind_the_push_summary(self):
        step = tool.Step("Fixture", [sys.executable, "-c", "print('fixture.py:12:3: broken'); raise SystemExit(1)"])
        output = io.StringIO()
        with mock.patch("sys.stdout", output):
            self.assertEqual(tool.run_step(step, "", hook=True), 1)
        self.assertTrue(output.getvalue().startswith("Push blocked: Fixture failed"))
        self.assertIn("fixture.py:12:3: broken", output.getvalue())

    def test_push_failure_is_the_first_line_and_keeps_full_diagnostics(self):
        output = io.StringIO()
        with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
            run.return_value = mock.Mock(returncode=1, stdout=b"Heading\napp.py:12:3: error\n")
            self.assertEqual(tool.run_step(tool.STEPS[2], "", hook=True), 1)
        self.assertTrue(output.getvalue().startswith("Push blocked: Verify launcher"))
        self.assertIn('Click "Show Command Output" for details.', output.getvalue().splitlines()[0])
        self.assertIn("app.py:12:3: error", output.getvalue())
        self.assertEqual(run.call_args.kwargs["stderr"], tool.subprocess.STDOUT)

    def test_locations_in_failed_output_get_links(self):
        # A traceback line and diagnostics relative to DONT_CHANGE (Ruff, Pyrefly); unknown files get none.
        config = tool.DONT_CHANGE_DIR / "scripts" / "config.py"
        output = tool.with_links(
            f'  File "{config}", line 12, in x\n'
            "scripts\\config.py:40:8: F401 unused\n"
            "  --> scripts/config.py:7:5\n"
            "no_such_file.py:3:1: E1 x"
        )
        link = config.resolve().as_uri()
        self.assertEqual(
            output.splitlines(),
            [
                f'  File "{config}", line 12, in x',
                f"    {link}#L12",
                "scripts\\config.py:40:8: F401 unused",
                f"    {link}#L40",
                "  --> scripts/config.py:7:5",
                f"    {link}#L7",
                "no_such_file.py:3:1: E1 x",
            ],
        )

    def test_a_blocked_push_lists_the_checks_that_did_not_run(self):
        output = io.StringIO()
        with mock.patch.object(tool, "run_step", return_value=1), mock.patch.object(
            tool.sys, "stdin", mock.Mock(read=lambda: "")
        ), mock.patch("sys.stdout", output):
            tool.main(["--pushing"])
        for step in tool.STEPS[1:]:
            self.assertRegex(output.getvalue(), rf"not run\s+{re.escape(step.label)}")

    def test_successful_push_steps_are_quiet_and_skips_are_not_failures(self):
        output = io.StringIO()
        with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
            for step, code in ((tool.STEPS[0], 0), (tool.STEPS[2], tool.SKIPPED)):
                run.return_value = mock.Mock(returncode=code, stdout=b"Heading\nMore output\n")
                self.assertEqual(tool.run_step(step, "refs", hook=True), code)
        self.assertEqual(output.getvalue(), "")
        self.assertIsNone(run.call_args.kwargs["input"])

    def test_leak_summary_is_kept_without_another_summary_in_front(self):
        output = io.StringIO()
        message = b"Push blocked: secret at app.py:12\nDetails\n"
        with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
            run.return_value = mock.Mock(returncode=1, stdout=message)
            self.assertEqual(tool.run_step(tool.STEPS[0], "refs", hook=True), 1)
        self.assertEqual(output.getvalue(), message.decode())
        self.assertEqual(run.call_args.kwargs["input"], b"refs")

    def run_main(self, codes: Dict[str, int], argv: List[str]) -> Tuple[int, List[str]]:
        """main() with fake step results; returns (exit code, labels of the steps that ran)."""
        ran: List[str] = []

        def fake_run(step: tool.Step, refs: str, *, hook: bool = False) -> int:
            ran.append(step.label)
            self.assertEqual(hook, "--pushing" in argv)
            if step.reads_refs:
                self.assertTrue(refs.startswith("refs/heads/"))
            return codes.get(step.label, 0)

        with mock.patch.object(tool, "run_step", side_effect=fake_run), mock.patch.object(
            tool, "refs_of_current_branch", return_value="refs/heads/dev a refs/heads/dev b\n"
        ), mock.patch.object(tool.sys, "stdin", mock.Mock(read=lambda: "refs/heads/x 1 refs/heads/x 2\n")), mock.patch(
            "builtins.print"
        ):
            return tool.main(argv), ran

    def test_everything_passes(self):
        code, ran = self.run_main({}, [])
        self.assertEqual(code, 0)
        self.assertEqual(ran, [step.label for step in tool.STEPS])

    def test_a_failure_is_reported_but_the_rest_still_runs(self):
        code, ran = self.run_main({"Repository check": 1}, [])
        self.assertEqual(code, 1)
        self.assertEqual(len(ran), len(tool.STEPS))

    def test_the_hook_stops_at_the_first_failure(self):
        code, ran = self.run_main({"Leak check": 1}, ["--pushing"])
        self.assertEqual((code, ran), (1, ["Leak check"]))

    def test_missing_ruff_or_pyrefly_skips_verification(self):
        code, _ = self.run_main({"Verify launcher (Ruff, Pyrefly)": tool.SKIPPED}, [])
        self.assertEqual(code, 0)
        code, _ = self.run_main({"Tests": tool.SKIPPED}, [])
        self.assertEqual(code, 1, "only verify_launcher may be skipped")

    def test_a_branch_without_a_remote_branch_is_compared_with_all_remotes(self):
        answers: Dict[Tuple[str, ...], str] = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "dev\n",
            ("rev-parse", "HEAD"): "abc\n",
        }

        def fake_git(*arguments: str) -> str:
            return answers.get(arguments, "")

        with mock.patch.object(tool, "git", side_effect=fake_git):
            self.assertEqual(tool.refs_of_current_branch(), f"refs/heads/dev abc refs/heads/dev {tool.NO_COMMIT}\n")


if __name__ == "__main__":
    unittest.main()

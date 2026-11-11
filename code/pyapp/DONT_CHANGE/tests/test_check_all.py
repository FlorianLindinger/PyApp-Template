"""pyapp_tools/check_all (and git_hooks/pre-push): every check at once, with a summary."""

from __future__ import annotations

import sys
import unittest
from typing import Dict, List, Tuple
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import _paths  # noqa: F401 - imported by the tool; the tools folder is only on sys.path here
    import check_all as tool


class CheckAllTests(unittest.TestCase):
    def run_main(self, codes: Dict[str, int], argv: List[str]) -> Tuple[int, List[str]]:
        """main() with fake step results; returns (exit code, labels of the steps that ran)."""
        ran: List[str] = []

        def fake_run(step: tool.Step, refs: str) -> int:
            ran.append(step.label)
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

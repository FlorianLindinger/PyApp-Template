"""pyapp_tools/check_all (and git_hooks/pre-push): every check at once, with a summary."""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools" / "src"), *sys.path]):
    import _paths  # noqa: F401 - imported by the tool; the tools folder is only on sys.path here
    import check_all as tool
    import check_changelog
    import check_protected

# By label, not position: steps can be added in between.
VERIFY = next(step for step in tool.STEPS if step.label.startswith("Verify launcher"))


@mock.patch.dict(os.environ, {"NO_COLOR": "1"})
class CheckAllTests(unittest.TestCase):
    def test_colored_failures_keep_the_same_summary_and_source_links(self):
        text = "\x1b[31mFAIL\x1b[0m: test_example (example.Tests.test_example)\n"
        self.assertEqual(tool.test_failure_reason(text, 1), tool.test_failure_reason(tool._ui.strip_ansi(text), 1))
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.py"
            source.write_text("raise ValueError()\n", encoding="utf-8")
            traceback = f'  File \x1b[35m"{source}"\x1b[0m, line \x1b[35m1\x1b[0m, in example\n'
            linked = tool.with_links(traceback)
            self.assertIn(source.resolve().as_uri(), linked)
            self.assertIn("\x1b[35m", linked)

    def test_settings_mismatch_is_explained_on_the_first_line(self):
        step = next(step for step in tool.STEPS if step.label == "Tests")
        reason = (
            "Settings mismatch: developer_settings.py does not match the fallback developer settings "
            "(dev_settings_default.py)."
        )
        diagnostics = (
            f"FAIL: test_defaults_file_is_identical_to_the_shipped_settings\nAssertionError: {reason}\n+ test package\n"
        )
        output = io.StringIO()
        with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
            run.return_value = mock.Mock(returncode=1, stdout=diagnostics.encode("utf-8"))
            self.assertEqual(tool.run_step(step, "", hook=True), 1)
        self.assertEqual(
            output.getvalue().splitlines()[0],
            f'Push blocked: {reason} Review both settings files and commit the correction. Click "Show Command Output" for details.',
        )
        self.assertIn(diagnostics, output.getvalue())

    def test_windows_child_line_endings_are_normalized_before_printing(self):
        output = io.StringIO()
        with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
            run.return_value = mock.Mock(returncode=1, stdout=b"Heading\r\nfixture.py:12:3: broken\r\n")
            self.assertEqual(tool.run_step(VERIFY, "", hook=True), 1)
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
            self.assertEqual(tool.run_step(VERIFY, "", hook=True), 1)
        self.assertTrue(output.getvalue().startswith("Push blocked: Launcher code checks failed"))
        self.assertIn('Click "Show Command Output" for details.', output.getvalue().splitlines()[0])
        self.assertIn("app.py:12:3: error", output.getvalue())
        self.assertEqual(run.call_args.kwargs["stderr"], tool.subprocess.STDOUT)
        self.assertEqual(run.call_args.kwargs["creationflags"], getattr(tool.subprocess, "CREATE_NO_WINDOW", 0))

    def test_other_check_failures_name_the_cause_before_the_full_output(self):
        cases = (
            (
                "Tests",
                "FAIL: test_stop_closes_children (Case)\nAssertionError: child survived",
                "Launcher test failed: stop closes children.",
            ),
            ("Tests", "Traceback: test runner could not start", "Launcher tests could not complete (exit code 1)."),
            (
                VERIFY.label,
                "Ruff lint   passed\nRuff format FAILED\nPyrefly     FAILED",
                "Launcher code checks failed: Ruff format, Pyrefly.",
            ),
            ("Repository check", "Tracked cache files\n  cache.pyc", "Repository file/path checks failed."),
        )
        for label, diagnostics, reason in cases:
            with self.subTest(label=label, reason=reason):
                output = io.StringIO()
                with mock.patch.object(tool.subprocess, "run") as run, mock.patch("sys.stdout", output):
                    run.return_value = mock.Mock(returncode=1, stdout=diagnostics.encode("utf-8"))
                    self.assertEqual(tool.run_step(tool.Step(label, []), "", hook=True), 1)
                self.assertIn(reason, output.getvalue().splitlines()[0])
                self.assertIn(diagnostics, output.getvalue())

    def test_compatibility_error_explains_the_protected_contract(self):
        output = io.StringIO()
        diagnostics = b"FAIL: test_protected_settings\nAssertionError: settings removed: old_name\n"
        with mock.patch.object(
            check_protected, "staged_paths", return_value=["code/pyapp/developer_settings.py"]
        ), mock.patch.object(
            check_protected.subprocess, "run", return_value=mock.Mock(returncode=1, stdout=diagnostics)
        ), mock.patch("sys.stdout", output):
            self.assertEqual(check_protected.main(), 1)
        first = output.getvalue().splitlines()[0]
        self.assertIn("Launcher compatibility check failed: settings removed: old_name", first)
        self.assertIn("PROTECTED_*", output.getvalue())
        self.assertIn("Review and stage the corrections", output.getvalue())

    def test_missing_dev_commands_have_a_readable_compatibility_headline(self):
        reason = (
            "Developer Tools commands missing from PROTECTED_DEV_TOOL_COMMANDS: install-requirements, reset-imports"
        )
        diagnostics = (
            "FAIL: test_scripts_outside_use_only_protected_commands\nAssertionError: "
            + reason
            + ". Add these commands to backend_settings.py.\n"
        )
        self.assertEqual(
            check_protected.first_problem(diagnostics),
            "Unregistered Developer Tools commands: install-requirements, reset-imports",
        )

    def test_file_contract_failures_start_with_the_repair(self):
        cases = (
            (
                "test_batch_and_settings_files_use_crlf",
                "AssertionError: 5 != 0 : install_requirements.cmd must use CRLF line endings",
                "install_requirements.cmd needs Windows CRLF line endings. Save with CRLF",
            ),
            (
                "test_the_file_tables_name_existing_files",
                "AssertionError: tests/README.md file table",
                "README file tables are missing or outdated. Update",
            ),
            (
                "test_every_test_file_is_in_exactly_one_group",
                "AssertionError: Lists differ",
                "Test files are missing from groups.py or listed twice. Register",
            ),
        )
        for name, diagnostic, expected in cases:
            with self.subTest(name=name):
                reason = tool.test_failure_reason(f"FAIL: {name}\n{diagnostic}", 1)
                self.assertTrue(reason.startswith(expected), reason)

    def test_multiple_test_failures_are_summarized_without_assertion_dumps(self):
        diagnostics = "\n".join(
            "FAIL: " + name
            for name in (
                "test_batch_and_settings_files_use_crlf",
                "test_the_file_tables_name_existing_files",
                "test_every_test_file_is_in_exactly_one_group",
            )
        )
        self.assertEqual(
            tool.test_failure_reason(diagnostics, 1),
            "3 launcher checks failed: CRLF line endings; README file tables; test-group registration. Fix the failures listed in the details.",
        )

    def test_repository_failure_names_the_issue_and_repair(self):
        step = tool.Step("Repository check", [])
        self.assertEqual(
            tool.failure_reason(step, 1, "── Tracked but ignored (2) ──\n  cache.pyc"),
            "Files matched by .gitignore are still tracked. Remove them from Git tracking.",
        )

    def test_a_check_that_cannot_start_has_a_push_headline(self):
        output = io.StringIO()
        with mock.patch.object(tool.subprocess, "run", side_effect=FileNotFoundError("python missing")), mock.patch(
            "sys.stdout", output
        ):
            self.assertEqual(tool.run_step(VERIFY, "", hook=True), 1)
        self.assertTrue(output.getvalue().startswith("Push blocked: Cannot start Verify launcher"))
        self.assertIn("python missing", output.getvalue())

    def test_hook_tool_errors_show_context_before_the_raw_exception(self):
        output = io.StringIO()
        with mock.patch("sys.stdout", output):
            result = tool._ui.run(
                mock.Mock(side_effect=OSError("repository inaccessible")), "Commit blocked: Cannot run the check."
            )
        self.assertEqual(result, 1)
        self.assertTrue(
            output.getvalue().startswith('Commit blocked: Cannot run the check. Click "Show Command Output"')
        )
        self.assertIn("repository inaccessible", output.getvalue())

    def test_compatibility_assertion_lists_are_not_copied_into_the_popup(self):
        diagnostics = "FAIL: test_protected_setting_names_still_exist\nAssertionError: Lists differ: ['old'] != ['new']"
        reason = check_protected.first_problem(diagnostics)
        self.assertEqual(reason, "Protected developer settings are missing from fallback defaults")
        self.assertNotIn("Lists differ", reason)

    def test_changelog_error_says_what_is_missing_and_which_branch_needs_it(self):
        output = io.StringIO()
        with mock.patch.object(
            check_changelog, "missing_changelog", return_value=[check_changelog.LAUNCHER + "x.py"]
        ), mock.patch("sys.stdout", output):
            self.assertEqual(check_changelog.main([]), 1)
        self.assertIn("Add a launcher CHANGELOG.md entry", output.getvalue().splitlines()[0])
        self.assertIn("changes to main", output.getvalue().splitlines()[0])
        self.assertIn(check_changelog.LAUNCHER + "x.py", output.getvalue())

    def test_locations_in_failed_output_get_links(self):
        # A traceback line and diagnostics relative to DONT_CHANGE (Ruff, Pyrefly); unknown files get none.
        config = tool.DONT_CHANGE_DIR / "scripts" / "config.py"
        output = tool.with_links(
            f'  File "{config}", line 12, in x\n'
            "    self.assertEqual(a, b)\n"
            "    ~~~~~~~~~~~~~~~~^^^^^^\n"
            "AssertionError: 1 != 2\n"
            "scripts\\config.py:40:8: F401 unused\n"
            "  --> scripts/config.py:7:5\n"
            "no_such_file.py:3:1: E1 x"
        )
        link = config.resolve().as_uri()
        self.assertEqual(
            output.splitlines(),
            [
                f'  File "{config}", line 12, in x',
                # After the traceback's source line and markers, so the traceback stays readable.
                "    self.assertEqual(a, b)",
                "    ~~~~~~~~~~~~~~~~^^^^^^",
                f"      {link}#L12",
                "AssertionError: 1 != 2",
                "scripts\\config.py:40:8: F401 unused",
                f"    {link}#L40",
                "  --> scripts/config.py:7:5",
                f"      {link}#L7",
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
            for step, code in ((tool.STEPS[0], 0), (VERIFY, tool.SKIPPED)):
                run.return_value = mock.Mock(returncode=code, stdout=b"Heading\nMore output\n")
                self.assertEqual(tool.run_step(step, "refs", hook=True), code)
        self.assertEqual(output.getvalue(), "")
        self.assertIsNone(run.call_args.kwargs["input"])

    def test_push_tests_receive_exact_refs_but_manual_tests_ignore_inherited_refs(self):
        step = next(item for item in tool.STEPS if item.label == "Tests")
        with mock.patch.object(tool.subprocess, "run", return_value=mock.Mock(returncode=0)) as run:
            tool.run_step(step, "exact pushed refs", hook=True)
            self.assertEqual(run.call_args.kwargs["env"]["PYAPP_SETTINGS_PUSH_REFS"], "exact pushed refs")
            with mock.patch.dict(tool.os.environ, {"PYAPP_SETTINGS_PUSH_REFS": "stale"}):
                tool.run_step(step, "ignored", hook=False)
            self.assertNotIn("PYAPP_SETTINGS_PUSH_REFS", run.call_args.kwargs["env"])

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


@unittest.skipIf(shutil.which("git") is None, "needs Git")
@mock.patch.dict(os.environ, {"NO_COLOR": "1"})
class ChangelogTests(unittest.TestCase):
    """pyapp_tools/check_changelog: a push to main that changes the launcher must touch its CHANGELOG.md."""

    def setUp(self):  # pyrefly: ignore[missing-override-decorator]
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.git("init", "-q", "-b", "main")
        self.base = self.commit({"README.md": "x"})
        patcher = mock.patch.object(check_changelog, "PROJECT_ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, *arguments: str) -> str:
        # Fixed Git commands in a temporary test repository.
        completed = subprocess.run(  # noqa: S603
            ["git", "-C", str(self.root), "-c", "user.name=T", "-c", "user.email=t@example.com", *arguments],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    def commit(self, files: Dict[str, str]) -> str:
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "change")
        return self.git("rev-parse", "HEAD")

    def push(self, branch: str = "main") -> List[str]:
        """What the check reports for pushing HEAD onto `branch` of a remote that has the first commit."""
        head = self.git("rev-parse", "HEAD")
        return check_changelog.missing_changelog(f"refs/heads/x {head} refs/heads/{branch} {self.base}\n")

    def test_launcher_changes_without_a_changelog_entry_are_reported(self):
        self.commit({"code/pyapp/DONT_CHANGE/scripts/a.py": "x"})
        self.assertEqual(self.push(), ["code/pyapp/DONT_CHANGE/scripts/a.py"])

    def test_a_changelog_entry_in_any_pushed_commit_is_enough(self):
        self.commit({"code/pyapp/DONT_CHANGE/scripts/a.py": "x"})
        self.commit({"code/pyapp/DONT_CHANGE/CHANGELOG.md": "- a change"})
        self.assertEqual(self.push(), [])

    def test_other_branches_notes_and_app_files_are_not_checked(self):
        self.commit(
            {"code/pyapp/DONT_CHANGE/TODO.md": "x", "code/pyapp/DONT_CHANGE/docs/TODO.md": "x", "code/main.py": "x"}
        )
        self.assertEqual(self.push(), [])
        self.commit({"code/pyapp/DONT_CHANGE/scripts/a.py": "x"})
        self.assertEqual(self.push("dev"), [])


if __name__ == "__main__":
    unittest.main()

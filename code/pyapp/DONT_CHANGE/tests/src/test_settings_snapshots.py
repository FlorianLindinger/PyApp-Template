"""Real disposable Git repos: index/commit settings checks must ignore unstaged local preferences."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project_location import CODE

# isort: split

from pyapp.DONT_CHANGE.scripts import settings_defaults as check


@unittest.skipUnless(shutil.which("git"), "Git required for snapshot regressions")
class SettingsSnapshotTests(unittest.TestCase):
    def prepare(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.git("init", "-q")
        self.write(check.PROJECT_SETTINGS, False)
        self.write(check.FALLBACK_SETTINGS, False)
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *arguments: str) -> str:
        # Every mutation is confined to this test's disposable repository, never the user's index.
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(self.root), "-c", "core.hooksPath=", *arguments],  # noqa: S607
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        return result.stdout

    def write(self, name: str, value: bool) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            'program_name = "PyApp-Template"\n# IMPORTANT:\n'
            f"replace_minimize_with_minimize_to_system_tray = {value!r}\n",
            encoding="utf-8",
        )

    def test_matching_index_ignores_unstaged_mismatch_and_working_test_still_detects_it(self):
        self.prepare()
        self.write(check.PROJECT_SETTINGS, True)
        before = self.git("write-tree")
        self.assertIsNone(check.settings_difference(self.root, ""))
        self.assertIn("working files", check.settings_difference(self.root) or "")
        self.assertEqual(self.git("write-tree"), before)
        self.assertIn("= True", (self.root / check.PROJECT_SETTINGS).read_text(encoding="utf-8"))

    def test_matching_working_files_cannot_hide_a_mismatched_index(self):
        self.prepare()
        self.write(check.PROJECT_SETTINGS, True)
        self.git("add", check.PROJECT_SETTINGS)
        self.write(check.PROJECT_SETTINGS, False)
        self.assertIsNone(check.settings_difference(self.root))
        self.assertIn("staged index", check.settings_difference(self.root, "") or "")

    def test_pushed_commit_is_checked_even_when_head_and_working_files_are_different(self):
        self.prepare()
        self.write(check.PROJECT_SETTINGS, True)
        self.git("add", check.PROJECT_SETTINGS)
        self.git(
            "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "-m", "mismatch"
        )
        other = self.git("rev-parse", "HEAD").strip()
        self.assertIsNone(check.settings_difference(self.root, self.base))
        self.assertIn(f"commit {other}", check.settings_difference(self.root, other) or "")
        refs = f"refs/heads/other {self.base} refs/heads/other {other}\n"
        with mock.patch.dict(os.environ, {check.PUSH_REFS_ENV: refs}):
            self.assertEqual(check.comparison_revisions(), [self.base])
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(check.comparison_revisions(), [None])

    def test_multiple_pushed_refs_skip_deletions_and_deduplicate_tips(self):
        self.prepare()
        zero = "0" * 40
        refs = f"refs/heads/a {self.base} refs/heads/a {zero}\nrefs/heads/b {self.base} refs/heads/b {zero}\n(deleted) {zero} refs/heads/c {self.base}\n"
        self.assertEqual(check.pushed_revisions(refs), [self.base])
        with self.assertRaises(ValueError):
            check.pushed_revisions("malformed input")

    def test_missing_staged_file_is_a_failure_and_comments_are_compared(self):
        self.prepare()
        self.git("rm", "--cached", check.FALLBACK_SETTINGS)
        with self.assertRaises(RuntimeError):
            check.settings_difference(self.root, "")
        path = self.root / check.FALLBACK_SETTINGS
        with path.open("a", encoding="utf-8") as stream:
            stream.write("# changed comment\n")
        self.assertIsNotNone(check.settings_difference(self.root))

    def test_cli_inspects_index_without_executing_or_changing_settings(self):
        self.prepare()
        script = self.root / "code/pyapp/DONT_CHANGE/scripts/settings_defaults.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_bytes((CODE / "pyapp/DONT_CHANGE/scripts/settings_defaults.py").read_bytes())
        self.write(check.PROJECT_SETTINGS, True)
        import sys

        # The trusted checker copy runs against only the fixture's index.
        result = subprocess.run([sys.executable, str(script), "--staged"], capture_output=True, check=False)  # noqa: S603
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git("add", check.PROJECT_SETTINGS)
        result = subprocess.run([sys.executable, str(script), "--staged"], capture_output=True, check=False)  # noqa: S603
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"Commit blocked:", result.stderr)
        self.assertIn(b"staged index", result.stderr)


if __name__ == "__main__":
    unittest.main()

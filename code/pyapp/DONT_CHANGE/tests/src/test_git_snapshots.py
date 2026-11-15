"""Real Git snapshots: code, configuration, refs and checkout policy belong to the submitted version."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "pyapp_tools/src"), *sys.path]):
    import git_snapshot as snapshots


@unittest.skipUnless(shutil.which("git"), "Git required")
class GitSnapshotTests(unittest.TestCase):
    def prepare(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.git("init", "-q")
        self.git("config", "core.autocrlf", "false")
        self.write("value.txt", "committed\n")
        self.write(".gitattributes", "*.txt text eol=crlf\n")
        for name in ("check_git_leaks", "check_staged_ruff", "check_protected"):
            self.write(f"code/pyapp/DONT_CHANGE/pyapp_tools/src/{name}.py", "raise SystemExit(0)\n")
        self.write("code/pyapp/DONT_CHANGE/scripts/settings_defaults.py", "raise SystemExit(0)\n")
        self.write("code/pyapp/DONT_CHANGE/pyapp_tools/src/check_all.py", "raise SystemExit(0)\n")
        self.git("add", ".")
        self.commit()

    def git(self, *args: str, data: bytes = b"") -> bytes:
        # All writes are confined to this disposable fixture.
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(self.root), "-c", "core.hooksPath=", *args],  # noqa: S607
            input=data,
            capture_output=True,
            check=True,
            env=snapshots.clean_environment(),
        )
        return result.stdout

    def write(self, name: str, text: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def commit(self) -> str:
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "-m", "fixture")
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_index_snapshot_includes_staged_code_config_and_attributes_only(self):
        self.prepare()
        self.write("value.txt", "staged\n")
        self.write("ruff.toml", '[lint]\nignore = ["F401"]\n')
        self.git("add", ".")
        index = (self.root / ".git/index").read_bytes()
        self.write("value.txt", "unstaged\n")
        self.write("ruff.toml", '[lint]\nselect = ["F401"]\n')
        self.write(".gitattributes", "*.txt text eol=lf\n")
        self.write("untracked.py", "raise RuntimeError('must not enter snapshot')\n")
        with snapshots.checkout(self.root) as root:
            self.assertEqual((root / "value.txt").read_bytes(), b"staged\r\n")
            self.assertIn("ignore", (root / "ruff.toml").read_text(encoding="utf-8"))
            self.assertFalse((root / "untracked.py").exists())
            location = root
        self.assertFalse(location.exists())
        self.assertEqual((self.root / ".git/index").read_bytes(), index)
        self.assertEqual((self.root / "value.txt").read_bytes(), b"unstaged\n")

    def test_hook_temporary_index_is_exported_without_leaking_into_snapshot_commands(self):
        self.prepare()
        alternate = self.root / "temporary-index"
        alternate.write_bytes((self.root / ".git/index").read_bytes())
        self.write("value.txt", "temporary index\n")
        env = snapshots.clean_environment()
        env["GIT_INDEX_FILE"] = str(alternate)
        # This separate temporary index models git commit with a pathspec.
        subprocess.run(["git", "-C", str(self.root), "add", "value.txt"], env=env, check=True, capture_output=True)  # noqa: S603 S607
        with mock.patch.dict(os.environ, {"GIT_INDEX_FILE": str(alternate)}), snapshots.checkout(self.root) as root:
            self.assertEqual((root / "value.txt").read_text(encoding="utf-8"), "temporary index\n")
        self.assertIn(b"committed", self.git("show", ":value.txt"))

    def test_staged_renames_deletions_and_intent_to_add_match_the_commit(self):
        self.prepare()
        self.git("mv", "value.txt", "renamed.txt")
        self.git("rm", ".gitattributes")
        self.write("pending.py", "not yet staged\n")
        self.git("add", "-N", "pending.py")
        with snapshots.checkout(self.root) as root:
            self.assertTrue((root / "renamed.txt").is_file())
            self.assertFalse((root / "value.txt").exists())
            self.assertFalse((root / ".gitattributes").exists())
            self.assertFalse((root / "pending.py").exists())

    def test_initial_commit_can_be_checked_before_head_exists(self):
        self.prepare()
        branch = self.git("symbolic-ref", "HEAD").decode().strip()
        self.git("update-ref", "-d", branch)
        with snapshots.checkout(self.root) as root:
            self.assertEqual((root / "value.txt").read_text(encoding="utf-8"), "committed\n")

    def test_real_ruff_reads_submitted_configuration(self):
        ruff = shutil.which("ruff")
        if ruff is None:
            self.skipTest("Ruff required for configuration integration check")
        self.prepare()
        self.write("probe.py", "import os\n")
        self.write("ruff.toml", '[lint]\nselect = ["F401"]\nignore = ["F401"]\n')
        self.git("add", ".")
        self.write("ruff.toml", '[lint]\nselect = ["F401"]\n')
        with snapshots.checkout(self.root) as root, mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(snapshots.run(self.root, root, [ruff, "check", "probe.py"]), 0)
        self.git("add", "ruff.toml")
        self.write("ruff.toml", '[lint]\nignore = ["F401"]\n')
        with snapshots.checkout(self.root) as root, mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(snapshots.run(self.root, root, [ruff, "check", "probe.py"]), 1)

    def test_pushed_non_head_commit_keeps_original_refs_and_ignores_working_files(self):
        self.prepare()
        first = self.git("rev-parse", "HEAD").decode().strip()
        self.git("update-ref", "refs/remotes/origin/base", first)
        self.write("value.txt", "later\n")
        self.git("add", ".")
        later = self.commit()
        self.write("value.txt", "local preference\n")
        with snapshots.checkout(self.root, first) as root:
            self.assertEqual((root / "value.txt").read_text(encoding="utf-8"), "committed\n")
            self.assertEqual(snapshots.git(root, "rev-parse", "HEAD").decode().strip(), first)
            self.assertEqual(snapshots.git(root, "rev-parse", "refs/remotes/origin/base").decode().strip(), first)
            # A shared mirror must not classify the source's unpublished commit as a remote tip.
            self.assertNotIn(
                later, snapshots.git(root, "for-each-ref", "--format=%(objectname)", "refs/remotes").decode()
            )

    def test_commit_checks_execute_staged_checker_code_and_fail_on_staged_errors(self):
        self.prepare()
        name = "code/pyapp/DONT_CHANGE/pyapp_tools/src/check_protected.py"
        self.write(name, "from pathlib import Path\nassert Path('value.txt').read_text().strip() == 'staged'\n")
        self.write("value.txt", "staged\n")
        self.git("add", ".")
        self.write(name, "raise RuntimeError('unstaged checker must not run')\n")
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(snapshots.commit_checks(self.root), 0)
        self.write(name, "raise SystemExit(17)\n")
        self.git("add", name)
        self.write(name, "raise SystemExit(0)\n")
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(snapshots.commit_checks(self.root), 17)

    def test_failure_headline_and_encoded_file_links_survive_snapshot_cleanup(self):
        self.prepare()
        with snapshots.checkout(self.root) as root, mock.patch("sys.stderr", io.StringIO()) as output:
            command = [
                sys.executable,
                "-c",
                "import sys; print('Push blocked: fixture'); print(sys.argv[1]); sys.exit(1)",
                (root / "value.txt").as_uri(),
            ]
            self.assertEqual(snapshots.run(self.root, root, command, scope="Submitted scope"), 1)
            lines = output.getvalue().splitlines()
            self.assertEqual(lines[:2], ["Push blocked: fixture", "Submitted scope"])
            self.assertEqual(lines[2], (self.root / "value.txt").as_uri())

    def test_push_checks_run_submitted_checker_for_every_tip_and_skip_deletions(self):
        self.prepare()
        first = self.git("rev-parse", "HEAD").decode().strip()
        name = "code/pyapp/DONT_CHANGE/pyapp_tools/src/check_all.py"
        self.write(name, "import sys\nassert sys.stdin.read()\nraise SystemExit(23)\n")
        self.git("add", name)
        second = self.commit()
        self.write(name, "raise SystemExit(0)\n")
        zero = "0" * 40
        refs = f"refs/heads/a {first} refs/heads/a {zero}\nrefs/heads/b {second} refs/heads/b {zero}\n"
        with mock.patch("sys.stderr", io.StringIO()) as output:
            self.assertEqual(snapshots.push_checks(refs, self.root), 23)
            self.assertIn(first, output.getvalue())
            self.assertIn(second, output.getvalue())
        with mock.patch.object(snapshots, "checkout") as export:
            self.assertEqual(snapshots.push_checks(f"(delete) {zero} refs/heads/a {first}\n", self.root), 0)
            export.assert_not_called()

    def test_unresolved_merges_and_non_isolated_entries_fail_closed(self):
        with self.assertRaises(RuntimeError):
            snapshots.validate_entries(b"100644 " + b"a" * 40 + b" 2\tconflict.py\0")
        with self.assertRaises(RuntimeError):
            snapshots.validate_entries(b"120000 " + b"a" * 40 + b" 0\toutside\0")


if __name__ == "__main__":
    unittest.main()

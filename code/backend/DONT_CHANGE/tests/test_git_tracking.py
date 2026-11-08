"""Guard: no ignore rule may hide a launcher file, so the folder keeps syncing through Git.

Asks Git itself (``git check-ignore``) which files in DONT_CHANGE are ignored. Caches and the
runtime folder are excluded on purpose; everything else must be trackable.
"""

import shutil
import subprocess
import unittest

from project_location import DONT_CHANGE, PROJECT_ROOT

# Generated or runtime folders that DONT_CHANGE/.gitignore is meant to hide.
EXCLUDED_PARTS = {"tmp", "__pycache__", ".ruff_cache"}


def git(*args, stdin=None):
    return subprocess.run(
        ["git", *args], cwd=str(PROJECT_ROOT), input=stdin, capture_output=True, text=True, check=False
    )


def inside_git_repository():
    if shutil.which("git") is None:
        return False
    result = git("rev-parse", "--is-inside-work-tree")
    return result.returncode == 0 and result.stdout.strip() == "true"


@unittest.skipUnless(inside_git_repository(), "not a git checkout")
class LauncherGitTrackingTests(unittest.TestCase):
    def test_no_launcher_file_is_ignored(self):
        files = [
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in DONT_CHANGE.rglob("*")
            if path.is_file()
            and not EXCLUDED_PARTS.intersection(path.relative_to(DONT_CHANGE).parts)
            and path.suffix != ".pyc"
        ]
        self.assertGreater(len(files), 50)
        # Without -v, check-ignore prints only the paths Git would ignore (exit 1 when none).
        result = git("check-ignore", "--stdin", stdin="\n".join(files) + "\n")
        self.assertIn(result.returncode, (0, 1), result.stderr)
        ignored = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(
            ignored,
            [],
            "these DONT_CHANGE files are hidden by an ignore rule; move the rule or add a "
            "negation after it in the root .gitignore:\n" + "\n".join(ignored),
        )


if __name__ == "__main__":
    unittest.main()

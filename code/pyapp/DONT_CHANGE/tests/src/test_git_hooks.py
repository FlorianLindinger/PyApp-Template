"""Exercise the shell hooks: diagnostics must reach Git clients through stderr."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from project_location import DONT_CHANGE


class HookOutputTests(unittest.TestCase):
    def run_hook(self, name: str, failing_tool: str) -> subprocess.CompletedProcess[str]:
        git = shutil.which("git")
        shell = shutil.which("sh")
        if shell is None and git is not None:
            candidate = Path(git).resolve().parents[1] / "bin" / "sh.exe"
            shell = str(candidate) if candidate.is_file() else None
        if git is None or shell is None:
            self.skipTest("Git and its shell are required to exercise the hooks")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            # Git only initializes this disposable fixture; no commit or push is performed.
            subprocess.run([git, "init", "-q", str(root)], check=True, capture_output=True)  # noqa: S603
            launcher = root / "code" / "pyapp" / "DONT_CHANGE"
            source = launcher / "pyapp_tools" / "src"
            source.mkdir(parents=True)
            (launcher / "tmp").mkdir()
            (launcher / "tmp" / "runtime.cmd").write_text(f'set "PYAPP_PYTHON={sys.executable}"\n', encoding="utf-8")
            for tool in ("check_git_leaks", "check_staged_ruff", "check_all"):
                script = ""
                if tool == failing_tool:
                    script = "import sys\n"
                    if name == "pre-push":
                        script += "assert sys.stdin.read().strip() == 'fixture refs'\n"
                    script += "print('Blocked: fixture.py:12:3: problem')\nraise SystemExit(1)\n"
                (source / (tool + ".py")).write_text(script, encoding="utf-8")
            # Execute the real hook, with local fixture tools in place of the application checks.
            return subprocess.run(  # noqa: S603
                [shell, str(DONT_CHANGE / "pyapp_tools" / "src" / "git_hooks" / name)],
                cwd=root,
                input="fixture refs\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=30,
            )

    def assert_failure_is_visible(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("Blocked: fixture.py:12:3: problem", result.stderr)

    def test_push_diagnostics_reach_stderr_and_refs_reach_the_check(self):
        self.assert_failure_is_visible(self.run_hook("pre-push", "check_all"))

    def test_commit_leak_diagnostics_reach_stderr(self):
        self.assert_failure_is_visible(self.run_hook("pre-commit", "check_git_leaks"))

    def test_commit_ruff_diagnostics_reach_stderr(self):
        self.assert_failure_is_visible(self.run_hook("pre-commit", "check_staged_ruff"))

    def test_a_passing_commit_is_silent_outside_a_terminal(self):
        # The success line is only for terminals; editors' Git output stays empty.
        result = self.run_hook("pre-commit", "")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()

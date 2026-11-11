"""Ruff lint and format check of the staged launcher files, for git_hooks/pre-commit.

Checks the staged content (what the commit will contain), not the files on disk, so changes that
are not staged cannot hide or cause a problem. Only Python files in code/pyapp/DONT_CHANGE, with
its own ruff.toml. Ruff comes from PATH, else uvx (see verify_launcher.py); without either, the
commit is not stopped, because a missing tool is not a problem in the code.

Usage: check_staged_ruff.py   (exit code 1: problems found)
"""

from __future__ import annotations

import re
import subprocess
from typing import List, Optional, Tuple

import _ui
from _paths import PROJECT_ROOT
from check_git_leaks import redacted_source
from verify_launcher import tool_command

LAUNCHER_PREFIX = "code/pyapp/DONT_CHANGE/"


def git(*arguments: str) -> bytes:
    # Fixed Git commands in the project folder.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), *arguments],  # noqa: S607
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip() or "git failed")
    return completed.stdout


def staged_python_files() -> List[str]:
    """Staged launcher .py files that the commit adds or changes (deleted ones need no check)."""
    names = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode("utf-8").split("\0")
    return [name for name in names if name.startswith(LAUNCHER_PREFIX) and name.endswith(".py")]


def run_ruff(ruff: List[str], arguments: List[str], name: str, content: bytes) -> Tuple[int, str]:
    """Ruff on content passed as the file `name` (so it finds that file's ruff.toml and exclusions)."""
    # Execute the Ruff command resolved from local PATH or uvx.
    completed = subprocess.run(  # noqa: S603
        [*ruff, *arguments, "--force-exclude", "--stdin-filename", name, "-"],
        cwd=str(PROJECT_ROOT),
        input=content,
        capture_output=True,
        check=False,
    )
    return completed.returncode, (completed.stdout + completed.stderr).decode("utf-8", "replace").strip()


def problems_in(ruff: List[str], name: str, content: bytes) -> List[str]:
    """Readable problems of one staged file ([] if it passes)."""
    found: List[str] = []
    code, output = run_ruff(ruff, ["check", "--no-fix", "--output-format", "concise"], name, content)
    if code:
        source_lines = content.decode("utf-8", "replace").splitlines()
        details: List[str] = []
        for diagnostic in output.splitlines():
            details.append(diagnostic)
            location = re.match(r"^.+:(\d+):\d+: ", diagnostic)
            if location and 1 <= int(location.group(1)) <= len(source_lines):
                details.append("    | " + redacted_source(source_lines[int(location.group(1)) - 1]))
        found.append("\n".join(details) or f"{name}: Ruff lint failed (exit code {code})")
    code, output = run_ruff(ruff, ["format", "--check"], name, content)
    if code:
        format_details = "\n".join(redacted_source(line) for line in output.splitlines())
        found.append(
            f"{name}: not formatted (run verify_launcher.bat --fix)" + ("\n" + format_details if format_details else "")
            if code == 1
            else output or f"{name}: Ruff format could not complete (exit code {code})"
        )
    return found


def main(ruff: Optional[List[str]] = None) -> int:
    names = staged_python_files()
    if not names:
        return 0
    if ruff is None:
        try:
            ruff = tool_command("ruff")
        except FileNotFoundError as error:
            _ui.warn(f"Ruff check before this commit skipped: {error}")
            return 0
    problems = [problem for name in names for problem in problems_in(ruff, name, git("show", ":" + name))]
    if not problems:
        return 0  # silent: this runs on every commit
    # Keep the first diagnostic in the first line for Git clients that truncate hook output.
    _ui.info(f'Commit blocked: Ruff: {problems[0].splitlines()[0]}. Click "Show Command Output" for details.')
    _ui.info("Locations refer to the staged files; unstaged edits can shift editor line numbers.")
    _ui.heading("Ruff diagnostics in staged launcher files")
    for problem in problems:
        _ui.info(problem)
    _ui.blank_line()
    _ui.error(
        "Fix the diagnostics, stage the corrected files, then commit again.\n"
        "verify_launcher.bat --fix applies safe Ruff fixes and formatting to working files.\n"
        "To commit anyway, once: git commit --no-verify"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))

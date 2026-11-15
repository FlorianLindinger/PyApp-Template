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
                number = int(location.group(1))
                details.append("    | " + redacted_source(source_lines[number - 1]))
                # Clickable in VS Code's "Show Command Output", where the relative path is only text.
                details.append("    " + _ui.file_link(PROJECT_ROOT / name, number))
        found.append("\n".join(details) or f"{name}: Ruff lint failed (exit code {code})")
    code, output = run_ruff(ruff, ["format", "--check"], name, content)
    if code:
        format_details = "\n".join(redacted_source(line) for line in output.splitlines())
        found.append(
            f"{name}: not formatted\n    {_ui.file_link(PROJECT_ROOT / name)}"
            + ("\n" + format_details if format_details else "")
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
    format_only = all(problem.splitlines()[0].endswith(": not formatted") for problem in problems)
    if format_only:
        count = len(problems)
        reason = f"{count} staged Python {'file needs' if count == 1 else 'files need'} formatting."
    else:
        # Keep the exact location for lint errors; formatting alone needs only a short count.
        diagnostic = next(problem for problem in problems if not problem.splitlines()[0].endswith(": not formatted"))
        reason = "Ruff: " + diagnostic.splitlines()[0] + "."
    action = (
        "Run verify_launcher.bat --fix, review and stage the files."
        if format_only
        else "Fix and stage the reported code."
    )
    _ui.info(f'Commit blocked: {reason} {action} Click "Show Command Output" for details.')
    _ui.heading("Formatting required" if format_only else "Ruff diagnostics in staged launcher files")
    for problem in problems:
        _ui.info(problem)
    _ui.heading("How to fix")
    _ui.info("1. Format the files above." if format_only else "1. Fix the diagnostics above.")
    _ui.info(
        "   Safe lint fixes and formatting: code\\pyapp\\DONT_CHANGE\\pyapp_tools\\verify_launcher.bat --fix\n"
        "2. Review and stage the corrected files.\n"
        "3. Commit again."
    )
    _ui.blank_line()
    _ui.info(
        "Ctrl+click a file:/// link to open the file. Line numbers refer to staged content.\n"
        "This check does not change files or staging."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(_ui.run(main, "Commit blocked: Ruff check could not complete. Check Git/Ruff availability."))

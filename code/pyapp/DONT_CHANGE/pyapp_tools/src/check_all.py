"""Run every check at once: the leak check, the repository check, verify_launcher and the tests.

    check_all.bat             before a push or release: checks the commits this branch has that its
                              remote does not, runs everything and shows a summary
    check_all.py --pushing    used by git_hooks/pre-push: reads the refs Git gives the hook and stops
                              at the first failure

The same steps as the pre-push hook, so a push holds no surprises. Without Ruff or Pyrefly,
verify_launcher is skipped rather than failed. Exit code 1 means a check failed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, NamedTuple, Optional

import _ui
from _paths import DONT_CHANGE_DIR, PROJECT_ROOT
from check_repository import git

SOURCE = Path(__file__).resolve().parent
TEST_RUNNER = DONT_CHANGE_DIR / "tests" / "src" / "run_regressions.py"
NO_COMMIT = "0" * 40
SKIPPED = 2  # verify_launcher's exit code when Ruff or Pyrefly is missing


class Step(NamedTuple):
    label: str
    command: List[str]
    reads_refs: bool = False  # the leak check gets the refs being pushed on stdin
    can_skip: bool = False


STEPS = (
    Step("Leak check", [sys.executable, "-B", str(SOURCE / "check_git_leaks.py"), "--pushing"], reads_refs=True),
    Step("Repository check", [sys.executable, "-B", str(SOURCE / "check_repository.py")]),
    Step("Verify launcher (Ruff, Pyrefly)", [sys.executable, "-B", str(SOURCE / "verify_launcher.py")], can_skip=True),
    Step("Tests", [sys.executable, "-B", "-X", "utf8", str(TEST_RUNNER), "-q", "-j", "0"]),
)


def refs_of_current_branch() -> str:
    """The line Git would give the pre-push hook for pushing this branch to its remote branch."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip() or "HEAD"
    local = git("rev-parse", "HEAD").strip()
    # Without a remote branch, the leak check compares with everything that is on any remote.
    remote = git("rev-parse", "@{upstream}").strip() or NO_COMMIT
    return f"refs/heads/{branch} {local} refs/heads/{branch} {remote}\n"


# A traceback line (File "D:\x\test_a.py", line 12) or a diagnostic (app.py:12:5: ... / --> app.py:12:5).
TRACEBACK_LOCATION = re.compile(r'^\s*File "([^"]+)", line (\d+)')
DIAGNOSTIC_LOCATION = re.compile(r"^\s*(?:-->\s*)?([^\s:\"]+(?::[\\/][^\s:\"]+)?):(\d+):\d+")


def with_links(output: str) -> str:
    """The output with a file:/// link under each line that names an existing file and line.

    VS Code's "Show Command Output" shows a failed push as plain text, where only full links can
    be clicked; relative diagnostics are resolved from the launcher folder (where Ruff and
    Pyrefly run) or the repository.
    """
    lines: List[str] = []
    for line in output.splitlines():
        lines.append(line)
        match = TRACEBACK_LOCATION.match(line) or DIAGNOSTIC_LOCATION.match(line)
        if not match:
            continue
        for base in (Path(), DONT_CHANGE_DIR, PROJECT_ROOT):
            path = base / match.group(1)
            if path.is_file():
                lines.append("    " + _ui.file_link(path, int(match.group(2))))
                break
    return "\n".join(lines)


def run_step(step: Step, refs: str, *, hook: bool = False) -> int:
    """Stream manual checks; buffer hook checks so a later failure gets the first output line."""
    completed = subprocess.run(  # noqa: S603
        step.command,
        input=refs.encode("utf-8") if step.reads_refs else None,
        stdout=subprocess.PIPE if hook else None,
        stderr=subprocess.STDOUT if hook else None,
        check=False,
    )
    if hook and completed.returncode and not (step.can_skip and completed.returncode == SKIPPED):
        # Normalize captured Windows line endings before print() translates them again.
        output = "\n".join(completed.stdout.decode("utf-8", "replace").splitlines()).strip()
        if output.startswith("Push blocked:"):
            _ui.info(output)  # the leak check's own report, with its first line and sections
        else:
            _ui.info(
                f"Push blocked: {step.label} failed (exit code {completed.returncode}). "
                'Click "Show Command Output" for details.'
            )
            if output:
                # Under its own heading, so it does not run into the summary of the checks below.
                _ui.heading(f"Output of {step.label}")
                _ui.info(with_links(output))
    return completed.returncode


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pushing", action="store_true", help="for the pre-push hook: reads its input, stops early")
    arguments = parser.parse_args(argv)
    refs = sys.stdin.read() if arguments.pushing else refs_of_current_branch()
    results: List[List[str]] = []
    failed = False
    # A push watched in a terminal shows each step as it finishes; editors (VS Code) get no extra
    # lines, so that a failure still starts with the "Push blocked: ..." line they display.
    live = arguments.pushing and _ui.interactive()
    if live:
        _ui.heading("Checks before the push")
    for step in STEPS:
        started = time.monotonic()
        if live:
            _ui.progress(f"  » {step.label} ...")
        code = run_step(step, refs, hook=arguments.pushing)
        status = "skipped" if step.can_skip and code == SKIPPED else "passed" if code == 0 else "FAILED"
        seconds = time.monotonic() - started
        results.append([step.label, status, f"{seconds:.1f} s"])
        if live:
            _ui.done(step.label, status != "FAILED", seconds, "skipped" if status == "skipped" else "")
        if status == "FAILED":
            failed = True
            if arguments.pushing:
                break  # the push stops anyway; no need to wait for the rest
    if not live:
        # A push stops at the first failure: the steps after it are listed as not run, so the
        # summary says what was and was not checked.
        results += [[step.label, "not run", ""] for step in STEPS[len(results) :]]
        _ui.heading("Checks before the push" if arguments.pushing else "All checks")
        # The table aligns all but the last column right: the names read best as that last one.
        _ui.table(("result", "time", "check"), [[status, seconds, label] for label, status, seconds in results])
    _ui.blank_line()
    if failed:
        how = "To push anyway, once: git push --no-verify" if arguments.pushing else "See the output above."
        _ui.error(f"A check failed. {how}")
        return 1
    if any(status == "skipped" for _, status, _ in results):
        _ui.warn("verify_launcher was skipped: put Ruff and Pyrefly on PATH, or install uv for uvx.")
    _ui.success("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))

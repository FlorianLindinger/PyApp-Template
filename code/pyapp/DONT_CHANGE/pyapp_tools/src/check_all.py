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
import subprocess
import sys
import time
from pathlib import Path
from typing import List, NamedTuple, Optional

import _ui
from _paths import DONT_CHANGE_DIR
from check_repository import git

SOURCE = Path(__file__).resolve().parent
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
    Step(
        "Tests",
        [sys.executable, "-B", "-X", "utf8", str(DONT_CHANGE_DIR / "tests" / "run_regressions.py"), "-q", "-j", "0"],
    ),
)


def refs_of_current_branch() -> str:
    """The line Git would give the pre-push hook for pushing this branch to its remote branch."""
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip() or "HEAD"
    local = git("rev-parse", "HEAD").strip()
    # Without a remote branch, the leak check compares with everything that is on any remote.
    remote = git("rev-parse", "@{upstream}").strip() or NO_COMMIT
    return f"refs/heads/{branch} {local} refs/heads/{branch} {remote}\n"


def run_step(step: Step, refs: str) -> int:
    # The tools of this folder, run with this interpreter; their output goes straight to the console.
    return subprocess.run(  # noqa: S603
        step.command,
        input=refs.encode("utf-8") if step.reads_refs else None,
        check=False,
    ).returncode


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pushing", action="store_true", help="for the pre-push hook: reads its input, stops early")
    arguments = parser.parse_args(argv)
    refs = sys.stdin.read() if arguments.pushing else refs_of_current_branch()
    results: List[List[str]] = []
    failed = False
    for step in STEPS:
        started = time.monotonic()
        code = run_step(step, refs)
        status = "skipped" if step.can_skip and code == SKIPPED else "passed" if code == 0 else "FAILED"
        results.append([step.label, status, f"{time.monotonic() - started:.1f} s"])
        if status == "FAILED":
            failed = True
            if arguments.pushing:
                break  # the push stops anyway; no need to wait for the rest
    _ui.heading("All checks")
    _ui.table(("check", "result", "time"), results)
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

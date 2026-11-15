"""A push to main that changes the launcher must also add to its CHANGELOG.md (git_hooks/pre-push).

    check_changelog.py --pushing    reads the lines Git gives the pre-push hook (as check_all passes them)

Only for main, where releases come from: other branches may collect changes first. Files that
are notes rather than the launcher (TODO.md, ...) do not count. Exit code 1: CHANGELOG.md was not
changed although launcher files were.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import List, Optional

import _ui
from _paths import PROJECT_ROOT

LAUNCHER = "code/pyapp/DONT_CHANGE/"
CHANGELOG = LAUNCHER + "CHANGELOG.md"
RELEASE_BRANCH = "refs/heads/main"
NOT_LAUNCHER = ("TODO.md", "docs/TODO.md", "future_TODO.md", "AGENT_CHANGELOG.md")  # notes, relative to DONT_CHANGE
NO_COMMIT = "0" * 40


def git(*arguments: str) -> str:
    # Fixed, read-only Git commands in the project folder.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), "-c", "core.quotepath=off", *arguments],  # noqa: S607
        capture_output=True,
        check=False,
    )
    return completed.stdout.decode("utf-8", "replace") if completed.returncode == 0 else ""


def changed_files(local: str, remote: str) -> List[str]:
    """The files the commits being pushed change (all of a new branch's commits not on a remote)."""
    known_remote = remote != NO_COMMIT and git("cat-file", "-t", remote).strip() == "commit"
    selection = [f"{remote}..{local}"] if known_remote else [local, "--not", "--remotes"]
    return sorted({name for name in git("log", "--format=", "--name-only", *selection).splitlines() if name})


def missing_changelog(hook_input: str) -> List[str]:
    """The launcher files pushed to main without a CHANGELOG.md change ([] if all is well)."""
    for line in hook_input.splitlines():
        fields = line.split()
        if len(fields) != 4 or fields[2] != RELEASE_BRANCH or fields[1] == NO_COMMIT:
            continue
        files = changed_files(fields[1], fields[3])
        launcher = [name for name in files if name.startswith(LAUNCHER) and name[len(LAUNCHER) :] not in NOT_LAUNCHER]
        if launcher and CHANGELOG not in files:
            return launcher
    return []


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pushing", action="store_true", help="read the refs being pushed from stdin")
    arguments = parser.parse_args(argv)
    hook_input = sys.stdin.read() if arguments.pushing else ""
    files = missing_changelog(hook_input)
    if not files:
        return 0
    _ui.info(
        "Push blocked: Add a launcher CHANGELOG.md entry before pushing launcher changes to main. "
        'Click "Show Command Output" for details.'
    )
    _ui.heading("Launcher files changed without a changelog entry")
    for name in files[:15]:
        _ui.info("  " + name)
    if len(files) > 15:
        _ui.info(f"  ... and {len(files) - 15} more")
    _ui.blank_line()
    _ui.error(
        f"Describe the change under the unreleased section of {CHANGELOG}\n"
        f"    {_ui.file_link(PROJECT_ROOT / CHANGELOG)}\n"
        "and commit it; people who update their projects read it. Only pushes to main are checked.\n"
        "To push anyway, once: git push --no-verify"
    )
    return 1


if __name__ == "__main__":
    context = (
        "Push blocked: Changelog check could not complete. Check Git/repository access."
        if "--pushing" in sys.argv
        else ""
    )
    raise SystemExit(_ui.run(main, context))

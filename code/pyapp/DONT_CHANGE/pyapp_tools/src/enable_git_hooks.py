"""Turn the template's Git hooks (git_hooks/pre-commit and pre-push) on or off for your own clones.

Setup never does this: Git hooks are a maintainer's choice, and people who clone the template must
not get them. This tool sets them up once per PC:

- in this clone: core.hooksPath (Git does not copy it with a clone), and
- in every clone of the same repository on this PC, now or later: a conditional include in your
  global Git configuration that applies only where a remote has this clone's origin URL
  (`includeIf "hasconfig:remote.*.url:..."`, Git 2.36 or newer). Clones of other repositories,
  and every other PC, are not affected.

Usage:

    enable_git_hooks.bat          turn the hooks on
    enable_git_hooks.bat --off    turn them off again (this clone and the global include)
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

import _ui
from _paths import PROJECT_ROOT

# Relative to the repository root, so the setting keeps working when the folder moves.
HOOKS_PATH = "code/pyapp/DONT_CHANGE/pyapp_tools/src/git_hooks"
# Holds only core.hooksPath; the global configuration includes it for matching repositories.
INCLUDED_FILE = "~/.gitconfig-pyapp-hooks"
MINIMUM_GIT = (2, 36)  # first version with includeIf "hasconfig:remote.*.url:"


def git(*arguments: str) -> Tuple[int, str]:
    """(exit code, output) of a Git command in this repository; the error output if it failed."""
    # Fixed Git commands in this project's repository.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(PROJECT_ROOT), *arguments],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, (completed.stderr if completed.returncode else completed.stdout).strip()


def git_version(text: str) -> Tuple[int, ...]:
    """(2, 52, 0) from "git version 2.52.0.windows.1"; () if there is no version in the text."""
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(part) for part in match.groups() if part is not None) if match else ()


def url_pattern(origin: str) -> str:
    """The include condition's pattern: this URL with or without ".git" (and a trailing slash)."""
    base = re.sub(r"(?:\.git)?/?$", "", origin.strip())
    return base + "**"


def include_key(origin: str) -> str:
    return f"includeIf.hasconfig:remote.*.url:{url_pattern(origin)}.path"


def turn_on(origin: str) -> List[str]:
    """Problems (empty when everything was set)."""
    problems: List[str] = []
    if git("config", "--local", "core.hooksPath", HOOKS_PATH)[0]:
        problems.append("Could not set core.hooksPath in this clone.")
    included = str(Path(INCLUDED_FILE).expanduser())
    if git("config", "--file", included, "core.hooksPath", HOOKS_PATH)[0]:
        problems.append(f'Could not write "{included}".')
    key = include_key(origin)
    code, existing = git("config", "--global", "--get-all", key)
    if (code or INCLUDED_FILE not in existing.splitlines()) and git("config", "--global", "--add", key, INCLUDED_FILE)[
        0
    ]:
        problems.append("Could not add the include to your global Git configuration.")
    return problems


def turn_off(origin: str) -> List[str]:
    problems: List[str] = []
    code, current = git("config", "--local", "--get", "core.hooksPath")
    if not code and current == HOOKS_PATH and git("config", "--local", "--unset", "core.hooksPath")[0]:
        problems.append("Could not remove core.hooksPath from this clone.")
    key = include_key(origin)
    if not git("config", "--global", "--get-all", key)[0] and git("config", "--global", "--unset-all", key)[0]:
        problems.append("Could not remove the include from your global Git configuration.")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--off", action="store_true", help="turn the hooks off again")
    arguments = parser.parse_args()
    _ui.heading("Git hooks: leak check before each commit, all checks before each push")
    try:
        code, origin = git("remote", "get-url", "origin")
        version = git_version(git("--version")[1])
    except FileNotFoundError:
        _ui.error("Git was not found on PATH.")
        return 2
    if code or not origin:
        _ui.error(
            "Could not read the URL of the remote named origin, which other clones are matched by: "
            + (origin or "there is no such remote.")
        )
        return 1
    _ui.fields([("Repository", origin), ("Hooks", HOOKS_PATH), ("Included file", INCLUDED_FILE)])
    _ui.blank_line()
    problems = turn_off(origin) if arguments.off else turn_on(origin)
    for problem in problems:
        _ui.error(problem)
    if problems:
        return 1
    if arguments.off:
        _ui.success("The hooks are off in this clone and in future clones of this repository on this PC.")
        return 0
    if version and version < MINIMUM_GIT:
        _ui.warn(
            f"Git {'.'.join(map(str, version))} is older than 2.36: the hooks are on in this clone, "
            "but other clones get them only after updating Git."
        )
    _ui.success("The hooks are on in this clone and in every clone of this repository on this PC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_ui.run(main))

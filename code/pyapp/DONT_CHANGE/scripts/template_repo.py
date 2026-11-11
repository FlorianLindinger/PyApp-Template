"""Things only the PyApp-Template repository itself does, never an app built from it.

Setup turns on the template's Git hooks (leak check before each commit and push) in a clone of
the template, so a maintainer gets them on every PC without remembering a command. Git never lets a
repository enable hooks by itself, and core.hooksPath is not copied by a clone, so an app made from
the template keeps its own Git configuration.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

from pyapp.DONT_CHANGE.backend_settings import SHORTCUT_OUTPUT_DIR

# Relative to the repository root, so the setting keeps working when the folder moves.
HOOKS_PATH = "code/pyapp/DONT_CHANGE/pyapp_tools/src/git_hooks"
# The same test as the template's GitHub Actions: a repository named PyApp-Template (any owner).
TEMPLATE_REMOTE = re.compile(r"[/:]PyApp-Template(?:\.git)?/?$", re.IGNORECASE)

GitRunner = Callable[[List[str]], Optional[str]]


def _git_runner(root: str) -> Optional[GitRunner]:
    git = shutil.which("git")
    if git is None:
        return None

    def run(arguments: List[str]) -> Optional[str]:
        """The output of a git command in the repository, or None if it failed."""
        # Fixed git commands in this project's repository.
        completed = subprocess.run(  # noqa: S603
            [git, "-C", root, *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    return run


def enable_template_git_hooks(root: str = SHORTCUT_OUTPUT_DIR, run: Optional[GitRunner] = None) -> bool:
    """Point core.hooksPath at the template's hooks in a clone of PyApp-Template; True if it was set now.

    Nothing happens in any other repository, without Git, or when core.hooksPath is already set
    (the maintainer's or a tool's own choice is never replaced).
    """
    if not (Path(root) / ".git").exists():
        return False
    run = run or _git_runner(root)
    if run is None:
        return False
    remote = run(["remote", "get-url", "origin"])
    if not remote or not TEMPLATE_REMOTE.search(remote):
        return False
    if run(["config", "--local", "--get", "core.hooksPath"]):
        return False
    return run(["config", "--local", "core.hooksPath", HOOKS_PATH]) is not None

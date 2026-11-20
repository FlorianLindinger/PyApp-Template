"""Clear messages for failed Git commands: what ran, what Git said, and what usually fixes it."""

from __future__ import annotations

import subprocess
from typing import Any, List, Sequence, Tuple, Union

MISSING = (
    "Git was not found. Install Git for Windows (https://git-scm.com/download/win), "
    "make sure git is on PATH, then open a new window."
)

# (text in Git's error output, what usually fixes it); the first match wins.
HINTS: Tuple[Tuple[str, str], ...] = (
    (
        "not a git repository",
        "This folder is not inside a Git repository. Clone the project, or run git init in the project folder.",
    ),
    (
        "dubious ownership",
        (
            "Git does not trust this folder because another Windows user owns it (common on external drives and"
            " copied folders). The command in Git's message above (git config --global --add safe.directory ...)"
            " allows it."
        ),
    ),
    (
        "index.lock",
        (
            "Another Git program is running, or a crashed one left .git/index.lock behind. Close other Git tools"
            " (editor, GitHub Desktop); if none is running, delete that file."
        ),
    ),
    ("does not have any commits yet", "The repository has no commit yet. Make a first commit, then run this again."),
    (
        "unknown revision",
        (
            "A commit, tag or branch this needs does not exist here (no commits yet, a shallow clone, or a missing"
            " tag). git fetch --tags --unshallow fetches the rest of a shallow clone."
        ),
    ),
    (
        "bad revision",
        "A commit, tag or branch this needs does not exist here (no commits yet, a shallow clone, or a missing tag).",
    ),
    (
        "permission denied",
        "Windows denied access to a file. Close programs that may hold it open (or an antivirus scan), then try again.",
    ),
    (
        "filename too long",
        (
            "A path is longer than Windows allows. Run git config --global core.longpaths true, or move the project"
            " to a shorter path."
        ),
    ),
)


def _text(output: Union[bytes, str, None]) -> str:
    if isinstance(output, bytes):
        return output.decode("utf-8", "replace")
    return output or ""


def explain(arguments: Sequence[str], returncode: int, stderr: Union[bytes, str, None]) -> str:
    """One readable message for a failed Git command, with a hint for the common causes."""
    lines = [line.strip() for line in _text(stderr).splitlines() if line.strip()]
    said = "\n  ".join(lines[:6]) if lines else "(no error output)"
    message = f'"git {" ".join(arguments)}" failed with exit code {returncode}:\n  {said}'
    lowered = " ".join(lines).lower()
    for needle, hint in HINTS:
        if needle in lowered:
            return message + "\nHint: " + hint
    return message


def run(command: List[str], *, check: bool = False, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """subprocess.run for a Git command; a missing Git becomes a RuntimeError that says so."""
    try:
        # Callers pass fixed Git commands.
        return subprocess.run(command, check=check, **kwargs)  # noqa: S603
    except FileNotFoundError:
        raise RuntimeError(MISSING) from None

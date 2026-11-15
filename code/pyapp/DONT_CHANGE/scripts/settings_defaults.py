"""Compare template settings in working files, the Git index, or a particular commit.

Read Git blobs as text rather than importing settings: checks must inspect exactly the content
being committed/pushed, without executing it or changing the user's working tree/index.
"""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_SETTINGS = "code/pyapp/developer_settings.py"
FALLBACK_SETTINGS = "code/pyapp/DONT_CHANGE/data/dev_settings_default.py"
PUSH_REFS_ENV = "PYAPP_SETTINGS_PUSH_REFS"


def settings_part(text: str) -> str:
    """Keep settings, values and comments; ignore compatibility annotations and the editor footer."""
    text = text.replace("\r\n", "\n")
    text = text[text.index("# IMPORTANT:\n") :]
    text = re.sub(r"(?m)^(\w+): [^=\n]+ =", r"\1 =", text)
    end = text.find("# open this file if someone runs it")
    return re.sub(r"\s*# =+\s*$", "", (text if end < 0 else text[:end]).rstrip())


def read_settings(root: Path, name: str, revision: Optional[str]) -> str:
    """None reads disk; an empty revision reads the index; otherwise read the named commit."""
    if revision is None:
        return (root / name).read_text(encoding="utf-8")
    # Fixed paths, a separate Git revision argument, and no shell or checkout operations.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "cat-file", "blob", f"{revision}:{name}"],  # noqa: S607
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"Cannot read {name} from {revision or 'the staged index'}: "
            + completed.stderr.decode("utf-8", "replace").strip()
        )
    return completed.stdout.decode("utf-8")


def settings_difference(root: Path, revision: Optional[str] = None) -> Optional[str]:
    """Return a mismatch with snapshot-specific source labels; downstream projects may customize settings."""
    project = read_settings(root, PROJECT_SETTINGS, revision)
    if not re.search(r'(?m)^program_name = "PyApp-Template"', project):
        return None
    fallback = read_settings(root, FALLBACK_SETTINGS, revision)
    project_lines = settings_part(project).splitlines()
    default_lines = settings_part(fallback).splitlines()
    if project_lines == default_lines:
        return None
    snapshot = "working files" if revision is None else (f"commit {revision}" if revision else "staged index")
    difference = "\n".join(
        difflib.unified_diff(
            default_lines,
            project_lines,
            fromfile=f"{FALLBACK_SETTINGS} ({snapshot})",
            tofile=f"{PROJECT_SETTINGS} ({snapshot})",
            lineterm="",
        )
    )
    return (
        "Settings mismatch: developer_settings.py does not match the fallback developer settings "
        "(dev_settings_default.py).\n"
        f"The shipped template must match in settings, values and comments in {snapshot}. "
        "Update both files for intentional template-default changes.\n" + difference
    )


def pushed_revisions(refs: str) -> List[str]:
    """Distinct non-deletion local tips from Git's pre-push input, including non-HEAD branches."""
    revisions: List[str] = []
    for line in refs.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 4 or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", fields[1]):
            raise ValueError("Invalid pre-push refs: expected local-ref local-commit remote-ref remote-commit.")
        revision = fields[1]
        if set(revision) != {"0"} and revision not in revisions:
            revisions.append(revision)
    return revisions


def comparison_revisions() -> List[Optional[str]]:
    """Hook tests compare the pushed tips; ordinary test runs continue to compare working files."""
    if PUSH_REFS_ENV in os.environ:
        return list(pushed_revisions(os.environ[PUSH_REFS_ENV]))
    return [None]


def main() -> int:
    if sys.argv[1:] != ["--staged"]:
        raise SystemExit("Usage: settings_defaults.py --staged")
    difference = settings_difference(Path(__file__).resolve().parents[4], "")
    if difference:
        print(
            "Commit blocked: Staged template settings differ from staged fallback defaults. "
            'Update and stage both files. Click "Show Command Output" for details.',
            file=sys.stderr,
        )
        print(difference, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f"Commit blocked: Settings comparison could not complete: {error}. "
            'Click "Show Command Output" for details.',
            file=sys.stderr,
        )
        raise SystemExit(1) from None

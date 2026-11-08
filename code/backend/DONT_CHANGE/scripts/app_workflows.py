"""GitHub Actions an app can switch on with the github_actions setting; Setup keeps their files up to date.

Only files named pyapp-app-*.yml are touched, so an app's own workflows are safe. To customize one
of these, rename it and take it off the list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

from backend.DONT_CHANGE.backend_settings import APP_WORKFLOW_SOURCE_DIR, APP_WORKFLOW_TARGET_DIR

FILE_PREFIX = "pyapp-app-"


def sync_app_workflows(
    wanted: Iterable[str], source_dir: str = APP_WORKFLOW_SOURCE_DIR, target_dir: str = APP_WORKFLOW_TARGET_DIR
) -> Tuple[List[str], List[str]]:
    """Make the folder match the setting; returns the names (added or updated, removed)."""
    target = Path(target_dir)
    changed: List[str] = []
    expected = set()
    for name in wanted:
        content = (Path(source_dir) / f"{name}.yml").read_bytes()
        path = target / f"{FILE_PREFIX}{name}.yml"
        expected.add(path.name)
        if not path.is_file() or path.read_bytes() != content:
            target.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            changed.append(name)
    removed: List[str] = []
    for path in sorted(target.glob(f"{FILE_PREFIX}*.yml")):
        if path.name not in expected:
            path.unlink()
            removed.append(path.stem[len(FILE_PREFIX) :])
    return changed, removed

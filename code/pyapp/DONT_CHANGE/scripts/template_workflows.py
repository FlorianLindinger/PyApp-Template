"""Setup removes the template's own GitHub workflows from an app made from the template.

The files .github/workflows/pyapp-template-*.yml test the template itself. Every job in them is
skipped unless the GitHub repository is named PyApp-Template, so in an app they never do anything
and only clutter the repository. Setup deletes them only when that is certain:

- the repository is not the template or a fork of it (its "origin" remote is not named
  PyApp-Template; a folder without Git is an app, too),
- .github holds nothing but the workflows folder, and that folder nothing but these files,
- each file is byte for byte (apart from line endings) a version the template has published.

Otherwise, e.g. when the app added its own workflow or changed one of these files, everything
stays as it is.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, FrozenSet, List

from pyapp.DONT_CHANGE.backend_settings import SHORTCUT_OUTPUT_DIR

# SHA-256 of every published version, after replacing CRLF with LF (Git may check out either).
# Only versions in which every job has "if: endsWith(github.repository, '/PyApp-Template')":
# the template's older fresh-clone.yml and launcher-tests.yml had no such condition and are not
# listed, so a folder that still holds one of them is left alone.
# After changing a workflow, add the hash that tests/src/test_template_workflows.py names.
KNOWN_TEMPLATE_WORKFLOWS: Dict[str, FrozenSet[str]] = {
    "pyapp-template-fresh-clone.yml": frozenset(
        {
            "1c1f136a6f4cfa4bb7537f6b1de566e8ccacad9b76f98149d824e11ebce01719",
            "73e264f0ebaf22ebc439c1556a5d97b8c9184eff3b9b5057ab8c243a988dcb91",
            "c387fc41e5076d3d22e366a8d6d50b93f90af5748beafeed9eca15d2f8e05b44",
        }
    ),
    "pyapp-template-launcher-tests.yml": frozenset(
        {
            "689a41b349d0d189080ddda94e797c14157bd4003c18ef880ca4348e8397ba6c",
            "926434145c2b828934965e7c70f4da896802a097a9aaf9576f48f0c40e9281ef",
            "ec69714227283873c6088f9590f1b02bef6ad5e511da8bd4f8a9a512f9cc5730",
        }
    ),
    "pyapp-template-weekly.yml": frozenset(
        {
            "1c25c76e90e24f3aa2627c99727018ecdbd21bba57d3059ccf864417423f2ead",
            "3498afc0304df4f28858cf16652ac716a3db364512ab782ad2fd1f2735299c57",
            "f2775988c6677d0ec9822eb4c18b692115e6919c7ba1e390fb533ff1e45c1c92",
        }
    ),
}
# The same test as the workflows' own condition, but ignoring case and a ".git" ending.
TEMPLATE_REMOTE = re.compile(r"[/:]PyApp-Template(?:\.git)?/?$", re.IGNORECASE)


def workflow_hash(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def is_template_repository(root: str) -> bool:
    """True for the template and its forks, and whenever that cannot be ruled out."""
    git = Path(root) / ".git"
    if not git.exists():
        return False  # a downloaded copy: an app
    if not git.is_dir():
        return True  # a worktree or submodule: its configuration is elsewhere, so keep everything
    try:
        config = (git / "config").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    # Read without Git, which may be missing: the url of [remote "origin"].
    section = re.search(r'(?ms)^\s*\[remote\s+"origin"\]\s*$(.*?)(?=^\s*\[|\Z)', config)
    if section is None:
        return False  # no origin: a local app repository
    urls = re.findall(r"(?m)^\s*url\s*=\s*(.+?)\s*$", section.group(1))
    return not urls or any(TEMPLATE_REMOTE.search(url.strip('"')) for url in urls)


def removable_template_workflows(root: str = SHORTCUT_OUTPUT_DIR) -> List[Path]:
    """The workflow files to delete, or [] when anything speaks against it."""
    github = Path(root) / ".github"
    workflows = github / "workflows"
    try:
        if not workflows.is_dir() or [entry.name for entry in github.iterdir()] != ["workflows"]:
            return []
        files = sorted(workflows.iterdir())
        if not files:
            return []
        for path in files:
            known = KNOWN_TEMPLATE_WORKFLOWS.get(path.name)
            if (
                known is None
                or not path.is_file()
                or path.is_symlink()
                or workflow_hash(path.read_bytes()) not in known
            ):
                return []
    except OSError:
        return []
    return [] if is_template_repository(root) else files


def remove_template_workflows(root: str = SHORTCUT_OUTPUT_DIR) -> List[str]:
    """Delete the template's own workflows from an app (see the module docstring); returns their names."""
    files = removable_template_workflows(root)
    removed: List[str] = []
    for path in files:
        try:
            path.unlink()
            removed.append(path.name)
        except OSError:
            break  # nothing else is touched; the next Setup tries again
    if removed and len(removed) == len(files):
        # Both folders are empty now: they held nothing else (checked above).
        try:
            (Path(root) / ".github" / "workflows").rmdir()
            (Path(root) / ".github").rmdir()
        except OSError:
            pass
    return removed

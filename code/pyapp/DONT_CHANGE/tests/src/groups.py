"""Named groups of test files, so one part of the launcher can be tested on its own.

Each group has a launcher in the tests folder (run_browser_tests.cmd runs the "browser" group), or run
"python run_regressions.py browser"; "--list" shows the groups. Every test file belongs to exactly
one group (test_files.py checks this), so a new test file must be added here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

TESTS = Path(__file__).resolve().parent
# The browser terminal is a standalone package with its own tests; they run here too.
PACKAGE_TESTS = TESTS.parents[1] / "browser_terminal" / "tests"
FOLDERS = (TESTS, PACKAGE_TESTS)

GROUPS: Dict[str, Tuple[str, ...]] = {
    # Starting and ending an app: wrapper, reports, logs, windows, shortcuts, processes.
    "app": (
        "test_entrypoint.py",
        "test_wrapper.py",
        "test_tracebacks.py",
        "test_output_logs.py",
        "test_logs.py",
        "test_shortcuts.py",
        "test_console_colors.py",
        "test_banner.py",
        "test_icons.py",
        "test_dev_menu.py",
        "test_windows.py",
        "test_fallback.py",
    ),
    # developer_settings.py, the environment, uv and Python, and what Setup changes in the project.
    "setup": (
        "test_settings.py",
        "test_packages.py",
        "test_resolve_runtime.py",
        "test_uv_fallback.py",
        "test_imports.py",
        "test_app_workflows.py",
        "test_template_workflows.py",
    ),
    # The browser terminal: its launcher side and the package's own tests.
    "browser": ("test_browser_terminal.py", "test_host.py"),
    # The Git hooks and the checks they run.
    "git": (
        "test_git.py",
        "test_git_hooks.py",
        "test_git_leaks.py",
        "test_staged_ruff.py",
        "test_check_all.py",
        "test_repository_check.py",
    ),
    # The maintainer tools in pyapp_tools.
    "tools": ("test_release.py", "test_tools.py", "test_verify_launcher.py", "test_import_map.py"),
    # Static checks of the shipped files: Python 3.8, line endings, references, what must stay stable.
    "files": ("test_files.py", "test_python38.py", "test_template_contract.py"),
}


def all_test_files() -> List[Path]:
    """Every test file of both test folders, in folder order."""
    return [path for folder in FOLDERS for path in sorted(folder.glob("test_*.py"))]


def group_files(name: str) -> List[Path]:
    """The files of one group (a listed file that does not exist is an error, not a silent skip)."""
    found = {path.name: path for path in all_test_files()}
    missing = [file for file in GROUPS[name] if file not in found]
    if missing:
        raise SystemExit(f"Group {name!r} names missing test files: {', '.join(missing)}")
    return [found[file] for file in GROUPS[name]]

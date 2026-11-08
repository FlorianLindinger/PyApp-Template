"""Dev tools for housekeeping: delete logs, remove shortcuts, show status."""

from __future__ import annotations

import os
import sys

from backend.DONT_CHANGE import backend_settings as paths
from backend.DONT_CHANGE.scripts.config import describe_python_request, display_path, settings, validate
from backend.DONT_CHANGE.scripts.console_tools import (
    ask,
    print_choices,
    print_fields,
    print_heading,
    print_info,
    print_success,
)
from backend.DONT_CHANGE.scripts.dev.common import confirm
from backend.DONT_CHANGE.scripts.diagnostics import diagnostics_summary, note_ignored
from backend.DONT_CHANGE.scripts.env.pyproject import current_requires_python, declared_dependencies
from backend.DONT_CHANGE.scripts.env.pythons import read_python_version_file, version_text
from backend.DONT_CHANGE.scripts.env.uv import uv_exe, uv_succeeds, uv_version
from backend.DONT_CHANGE.scripts.env.venv import read_venv_config, venv_home_valid, venv_version
from backend.DONT_CHANGE.scripts.errors import SettingsError, SetupError


def cmd_clean(arguments):
    """Delete logs or run diagnostics."""
    from backend.DONT_CHANGE.scripts.filesystem_tools import remove_tree_inside
    from backend.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

    s = settings()
    log_folder = get_log_folder_path(s.log_path, s.log_path_is_relative_to_start_folder_if_relative)
    crash_folder = get_log_folder_path(s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative)
    options = [
        (
            "logs",
            f"Delete all files in the log folder ({display_path(log_folder) if log_folder else 'disabled'})",
        ),
        (
            "crash",
            f"Delete all files in the crash log folder ({display_path(crash_folder) if crash_folder else 'disabled'})",
        ),
        ("runs", "Delete per-run diagnostics (tmp\\runs)"),
    ]
    print_heading("Clean")
    print_choices(label for _, label in options)
    chosen = ask("Numbers to clean (space separated), Enter = cancel:").replace(",", " ").split()
    keys = {options[int(c) - 1][0] for c in chosen if c.isdigit() and 1 <= int(c) <= len(options)}
    if not keys or not confirm("Delete permanently?"):
        return
    for key, folder in (("logs", log_folder), ("crash", crash_folder)):
        if key in keys and folder and os.path.isdir(folder):
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isfile(path) and name != ".gitkeep":
                    os.remove(path)
    if "runs" in keys and os.path.isdir(paths.RUNS_DIR):
        remove_tree_inside(paths.RUNS_DIR, paths.TEMPORARY_DIR)
    print_success("Cleaned.")


def cmd_remove_shortcuts(arguments):
    """Remove every shortcut Setup created (project folder, Start Menu, Desktop)."""
    from backend.DONT_CHANGE.scripts.shortcuts import (
        read_created_shortcuts,
        remove_shortcuts,
        write_created_shortcuts,
    )

    removed = remove_shortcuts(read_created_shortcuts())
    write_created_shortcuts([])
    for path in removed:
        print_info("Removed: " + path)
    print_success(f"Removed {len(removed)} shortcut(s). Run Setup to create them again.")


def cmd_status(arguments):
    """Show uv, Python, environment and shortcut state."""
    s = settings()
    try:
        validate(s)
        settings_state = "valid"
    except SettingsError as error:
        settings_state = str(error)
    try:
        uv = uv_exe()
        uv_state = f"{uv_version()} at {uv}" + (
            " (local)" if os.path.normcase(uv).startswith(os.path.normcase(paths.LOCAL_UV_DIR)) else " (global)"
        )
    except SetupError:
        uv = None
        uv_state = "missing (Setup or the next start installs it)"
    config = read_venv_config()
    lock_state = ("(missing - created on the next start)", False)
    if os.path.isfile(paths.UV_LOCK_PATH) and uv is None:
        lock_state = ("present (not checked: uv is missing)", False)
    elif os.path.isfile(paths.UV_LOCK_PATH):
        up_to_date = uv_succeeds(["lock", "--check", "--offline"])
        lock_state = ("up to date", True) if up_to_date else ("needs an update (next start or sync)", False)
    try:
        from backend.DONT_CHANGE.scripts.shortcuts import read_created_shortcuts

        shortcut_count = f"{len(read_created_shortcuts())} created by Setup"
    except Exception:
        note_ignored("cmd_status: shortcut list")
        shortcut_count = "?"
    ignored = diagnostics_summary()
    in_sync = declared_dependencies() == list(s.packages)
    sections: dict[str, list[tuple]] = {
        "Project": [
            ("Program", s.program_name),
            ("Launcher version", paths.LAUNCHER_VERSION),
            ("Settings", settings_state, settings_state == "valid"),
            ("Shortcuts", shortcut_count),
            (
                "Ignored errors",
                f"{ignored} (see {display_path(paths.DIAGNOSTICS_LOG_PATH)})" if ignored else "none",
                not ignored,
            ),
        ],
        "uv and Python": [
            ("uv", uv_state, uv is not None),
            ("Launcher Python", f"{version_text(sys.version_info[:3])} at {sys.executable}"),
            ("python_version", describe_python_request(s.python_version)),
            ("python_source", s.python_source),
            ("backend/env/.python-version", read_python_version_file() or "(missing)"),
            ("requires-python", current_requires_python() or "(missing)"),
        ],
        "Packages": [
            ("packages", ", ".join(s.packages) or "(none)"),
            (
                "pyproject.toml",
                "matches developer_settings.py" if in_sync else "differs (updated on the next start or dev tool)",
                in_sync,
            ),
            ("uv.lock", *lock_state),
        ],
        "Environment": [("Folder", display_path(paths.VENV_DIR) if config else "(not created)", bool(config))],
    }
    if config:
        sections["Environment"] += [
            ("Python", version_text(venv_version(config) or ())),
            (
                "Base Python",
                config.get("home", "?")
                + ("" if venv_home_valid(config) else "  (MISSING - repaired on the next start)"),
                venv_home_valid(config),
            ),
            ("Relocatable", config.get("relocatable", "false")),
        ]
    for title, rows in sections.items():
        print_heading(title)
        print_fields(rows)


def cmd_test(arguments):
    """Run the launcher's regression tests (DONT_CHANGE/tests); optional file pattern."""
    import subprocess

    script = os.path.join(paths.DONT_CHANGE_DIR, "tests", "run_regressions.py")
    if not os.path.isfile(script):
        print_info("The tests folder DONT_CHANGE/tests was removed; nothing to run.")
        return
    print_heading("Launcher tests")
    code = subprocess.run([sys.executable, "-B", script, "-q", *arguments], check=False).returncode
    print()
    if code:
        raise SetupError("Some launcher tests failed (see above).")
    print_success("All launcher tests passed.")

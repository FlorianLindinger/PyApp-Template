"""Dev tools for housekeeping: delete logs, remove shortcuts, show status."""

from __future__ import annotations

import os
import sys

from backend.DONT_CHANGE import backend_settings as paths
from backend.DONT_CHANGE.scripts.config import describe_python_request, display_path, settings, validate
from backend.DONT_CHANGE.scripts.console_tools import input_warn, print_success
from backend.DONT_CHANGE.scripts.dev.common import ask
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
    for index, (_, label) in enumerate(options, 1):
        print(f"  {index}: {label}")
    chosen = input_warn("Numbers to clean (space separated), Enter = cancel: ").replace(",", " ").split()
    keys = {options[int(c) - 1][0] for c in chosen if c.isdigit() and 1 <= int(c) <= len(options)}
    if not keys or not ask("Delete permanently?"):
        return
    for key, folder in (("logs", log_folder), ("crash", crash_folder)):
        if key in keys and folder and os.path.isdir(folder):
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isfile(path) and name != ".gitkeep":
                    os.remove(path)
    if "runs" in keys and os.path.isdir(paths.RUNS_DIR):
        remove_tree_inside(paths.RUNS_DIR, paths.TEMPORARY_DIR)
    print_success("[Success] Cleaned.")


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
        print("[Info] Removed: " + path)
    print_success(f"[Success] Removed {len(removed)} shortcut(s). Run Setup to create them again.")


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
    lines = [
        ("Program", s.program_name),
        ("Settings", settings_state),
        ("python_version", describe_python_request(s.python_version)),
        ("python_source", s.python_source),
        ("package_environment", s.package_environment),
        ("uv", uv_state),
        (
            "Launcher Python",
            f"{version_text(sys.version_info[:3])} at {sys.executable}",
        ),
        ("backend/.python-version", read_python_version_file() or "(missing)"),
        ("requires-python", current_requires_python() or "(missing)"),
        ("packages", ", ".join(s.packages) or "(none)"),
        (
            "pyproject.toml",
            "matches developer_settings.py"
            if declared_dependencies() == list(s.packages)
            else "differs (updated on the next start or dev tool)",
        ),
        ("Environment", display_path(paths.VENV_DIR) if config else "(not created)"),
    ]
    if config:
        lines += [
            ("  Python", version_text(venv_version(config) or ())),
            (
                "  base",
                config.get("home", "?") + ("" if venv_home_valid(config) else "  (MISSING - repaired on next start)"),
            ),
            ("  relocatable", config.get("relocatable", "false")),
        ]
    if os.path.isfile(paths.UV_LOCK_PATH) and uv is None:
        lines.append(("uv.lock", "present (not checked: uv is missing)"))
    elif os.path.isfile(paths.UV_LOCK_PATH):
        code = 0 if uv_succeeds(["lock", "--check", "--offline"]) else 1
        lines.append(
            (
                "uv.lock",
                "up to date" if code == 0 else "needs an update (next start or sync)",
            )
        )
    else:
        lines.append(("uv.lock", "(missing - created on next start)"))
    try:
        from backend.DONT_CHANGE.scripts.shortcuts import read_created_shortcuts

        lines.append(("Shortcuts", f"{len(read_created_shortcuts())} created by Setup"))
    except Exception:
        note_ignored("cmd_status: shortcut list")
    lines.append(
        (
            "Downloads at launch",
            "allowed" if s.allow_downloads_at_launch else "disabled",
        )
    )
    ignored = diagnostics_summary()
    lines.append(
        (
            "Ignored errors",
            f"{ignored} (see {display_path(paths.DIAGNOSTICS_LOG_PATH)})" if ignored else "none",
        )
    )
    width = max(len(label) for label, _ in lines)
    for label, value in lines:
        print(f"{label.ljust(width)} : {value}")

"""Setup: prepare uv, Python and the packages, then create the shortcuts and remove stale ones.

Run by "Setup - run first and after moving folder.cmd".
"""

from __future__ import annotations

import os

from backend.DONT_CHANGE.backend_settings import DEV_SETTINGS_PATH, SHORTCUT_OUTPUT_DIR
from backend.DONT_CHANGE.scripts.banner import print_banner
from backend.DONT_CHANGE.scripts.config import settings, validate
from backend.DONT_CHANGE.scripts.filesystem_tools import make_abs_path_relative_to_file, sanitize_filename
from backend.DONT_CHANGE.scripts.shortcuts import (
    CSIDL_DESKTOPDIRECTORY,
    CSIDL_PROGRAMS,
    generate_shortcut,
    project_app_id,
    read_created_shortcuts,
    remove_shortcuts,
    shortcut_definitions,
    shortcut_filename,
    shortcut_targets,
    special_folder,
    write_created_shortcuts,
)

pause_on_success = True


def main() -> None:
    """Optionally prepare the environment, then create the enabled shortcuts and remove stale ones."""
    s = settings()
    validate(s)
    print_banner()
    app_id = project_app_id(s.program_name)
    targets_by_kind = shortcut_targets(s)
    definitions = shortcut_definitions(s, app_id, targets_by_kind)
    filenames = [shortcut_filename(d[1]).casefold() for d in definitions]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Shortcut names collide after Windows filename sanitization; choose distinct names.")
    if s.install_environment_when_generating_shortcuts:
        from backend.DONT_CHANGE.scripts.env.venv import ensure_environment

        ensure_environment(interactive=True)
    if s.user_settings_path:
        settings_file = make_abs_path_relative_to_file(s.user_settings_path, DEV_SETTINGS_PATH)
        if not os.path.exists(settings_file):
            print(
                f'[Warning] The user settings file does not exist: "{settings_file}". Its shortcut will show an error until the file exists.'
            )
    for kind in ("logs", "crash_logs"):
        if targets_by_kind[kind]:
            os.makedirs(targets_by_kind[kind], exist_ok=True)  # the shortcut opens it right away

    targets = [SHORTCUT_OUTPUT_DIR]
    start_menu = None
    if s.start_menu_shortcuts:
        start_menu = os.path.join(special_folder(CSIDL_PROGRAMS), sanitize_filename(s.program_name))
        targets.append(start_menu)
    print()
    print("=" * 30)
    created = []
    for kind, name, icon, launcher, args, shortcut_app_id, description in definitions:
        folders = list(targets)
        if kind in s.desktop_shortcuts:
            folders.append(special_folder(CSIDL_DESKTOPDIRECTORY))
        for folder in folders:
            created.append(
                generate_shortcut(
                    name,
                    icon,
                    launcher,
                    args=args,
                    app_id=shortcut_app_id,
                    description=description,
                    start_minimized=kind != "stop",  # Stop shows a short countdown
                    output_dir=folder,
                )
            )
    removed = remove_shortcuts(read_created_shortcuts(), keep=created)
    write_created_shortcuts(created, targets_by_kind)
    print()
    for path in removed:
        print(f"[Info] Removed old shortcut: {path}")
    print(f"Shortcuts created in: {SHORTCUT_OUTPUT_DIR}")
    if start_menu:
        print(f"Start Menu folder: {start_menu}")
    if s.desktop_shortcuts:
        print("Desktop: " + ", ".join(s.desktop_shortcuts))
    print("=" * 30)

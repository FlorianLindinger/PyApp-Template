"""Setup: prepare uv, Python and the packages, then create the shortcuts and remove stale ones.

Run by "Setup - run first and after moving folder.cmd".
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from pyapp.DONT_CHANGE.pyapp_settings import (
    DEV_SETTINGS_PATH,
    ICON_PATH,
    INSTALL_ENVIRONMENT_WHEN_GENERATING_SHORTCUTS,
    LAUNCHER_VERSION,
    SHORTCUT_OUTPUT_DIR,
)
from pyapp.DONT_CHANGE.scripts.banner import print_banner
from pyapp.DONT_CHANGE.scripts.config import settings, validate
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    ANSI_GOOD,
    print_heading,
    print_success,
    print_warn,
    styled,
)
from pyapp.DONT_CHANGE.scripts.desktop.shortcuts import (
    CSIDL_DESKTOPDIRECTORY,
    CSIDL_PROGRAMS,
    create_windows_startup_shortcut,
    generate_shortcut,
    leftover_shortcuts,
    project_app_id,
    read_created_shortcuts,
    read_start_link,
    remove_shortcuts,
    shortcut_definitions,
    shortcut_filename,
    shortcut_targets,
    special_folder,
    write_created_shortcuts,
)
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
from pyapp.DONT_CHANGE.scripts.github.app_workflows import sync_app_workflows
from pyapp.DONT_CHANGE.scripts.github.template_workflows import remove_template_workflows
from pyapp.DONT_CHANGE.scripts.launcher_ui import delete_finished_run_folders
from pyapp.DONT_CHANGE.scripts.standalone.file_tools import make_abs_path_relative_to_file, sanitize_filename

pause_on_success = True


def _short(path: str) -> str:
    """A path for display, with the user profile folder as %USERPROFILE%."""
    home = str(Path("~").expanduser())
    if os.path.normcase(path).startswith(os.path.normcase(home) + os.sep):
        return "%USERPROFILE%" + path[len(home) :]
    return path


def _short_name(name: str, program_name: str) -> str:
    """ "App (Logs)" as "Logs" for the compact list; other names unchanged."""
    rest = name[len(program_name) :].strip() if name.startswith(program_name) else ""
    if rest.startswith("(") and rest.endswith(")"):
        return rest[1:-1].strip() or name
    return name


def sync_start_link(s: object, app_id: str) -> str:
    """Register the browser terminal's start link (with its shortcut), remove an outdated one; returns its scheme."""
    from pyapp.DONT_CHANGE.scripts import browser_links

    previous = read_start_link()
    current = ""
    try:
        if getattr(s, "browser_terminal_shortcut_name", ""):
            name = browser_links.scheme(app_id)
            if browser_links.register_start_link(name, app_id, ICON_PATH):
                current = name
            else:
                print_warn(
                    f'"{name}://" belongs to another program, so there is no start link for the browser terminal.'
                )
        # E.g. after renaming the program or disabling the browser terminal shortcut.
        if previous and previous != current:
            browser_links.unregister_start_link(previous)
    except OSError:
        note_ignored("browser terminal start link")
    return current


def main() -> None:
    """Optionally prepare the environment, then create the enabled shortcuts and remove stale ones."""
    s = settings()
    validate(s)
    print_banner()
    print(
        styled(f"Launcher {LAUNCHER_VERSION}. Run Setup again after moving or renaming the project folder.", ANSI_DIM)
    )
    app_id = project_app_id(s.program_name)
    targets_by_kind = shortcut_targets(s)
    definitions = shortcut_definitions(s, app_id)
    filenames = [shortcut_filename(d[1]).casefold() for d in definitions]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Shortcut names collide after Windows filename sanitization; choose distinct names.")
    if INSTALL_ENVIRONMENT_WHEN_GENERATING_SHORTCUTS:
        from pyapp.DONT_CHANGE.scripts.env.pythons import interpreter_version, version_text
        from pyapp.DONT_CHANGE.scripts.env.venv import ensure_environment

        print_heading("Environment")
        app = ensure_environment(interactive=True)
        where = "pyapp\\generated\\.venv"
        print(
            f"  {styled('ready', ANSI_GOOD)}  Python {version_text(interpreter_version(app.exe))}  {styled(where, ANSI_DIM)}"
        )
    if s.user_settings_path:
        settings_file = make_abs_path_relative_to_file(s.user_settings_path, DEV_SETTINGS_PATH)
        if not Path(settings_file).exists():
            print()
            print_warn(
                f'The user settings file does not exist: "{settings_file}". '
                "Change user_settings_path in developer_settings.py, or make sure the file exists at this path. "
                'Set user_settings_path = "" to disable the Settings shortcut.'
            )
    for kind in ("logs", "crash_logs"):
        if targets_by_kind[kind]:
            Path(targets_by_kind[kind]).mkdir(parents=True, exist_ok=True)  # so the shortcut can open it right away

    removed_template_workflows: List[str] = []
    try:
        # Before the app's own workflows are added, which would count as "something else".
        removed_template_workflows = remove_template_workflows()
    except Exception:
        note_ignored("remove_template_workflows")  # tidying only; the files do nothing in an app
    added, removed_workflows = sync_app_workflows(s.github_actions)
    if added or removed_workflows or removed_template_workflows:
        print_heading("GitHub Actions")
        for name in removed_template_workflows:
            print(
                f"  {styled('-', ANSI_DIM)} {styled('removed ' + name + ' (tests of the template itself)', ANSI_DIM)}"
            )
        for name in added:
            print(f"  {styled('+', ANSI_GOOD)} {name}")
        for name in removed_workflows:
            print(f"  {styled('-', ANSI_DIM)} {styled('removed ' + name, ANSI_DIM)}")

    folders_by_label = [("project folder", SHORTCUT_OUTPUT_DIR)]
    if s.start_menu_shortcuts:
        start_menu = str(Path(special_folder(CSIDL_PROGRAMS)) / sanitize_filename(s.program_name))
        folders_by_label.append(("Start Menu", start_menu))
    desktop = special_folder(CSIDL_DESKTOPDIRECTORY) if s.desktop_shortcuts else None
    print_heading("Shortcuts")
    created: List[str] = []
    previous = read_created_shortcuts()
    names_by_places: Dict[str, List[str]] = {}  # one line per set of places, not per shortcut
    try:
        for kind, name, icon, launcher, args, shortcut_app_id, description in definitions:
            places = list(folders_by_label)
            if desktop and kind in s.desktop_shortcuts:
                places.append(("Desktop", desktop))
            for _, folder in places:
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
            names_by_places.setdefault(", ".join(label for label, _ in places), []).append(
                _short_name(name, s.program_name)
            )
        for where, names in names_by_places.items():
            print(f"  {styled('+', ANSI_GOOD)} {len(names)} in {where}  {styled(', '.join(names), ANSI_DIM)}")
        startup_shortcut = create_windows_startup_shortcut(s, app_id)
        if startup_shortcut:
            created.append(startup_shortcut)
            print(f"  {styled('+', ANSI_GOOD)} Windows sign-in  {styled(_short(startup_shortcut), ANSI_DIM)}")
    except BaseException:
        # Stopped halfway (e.g. a Desktop write blocked by Controlled Folder Access): record every
        # shortcut that exists now, so the next Setup or remove_shortcuts still knows about it.
        write_created_shortcuts(previous + created, read_start_link())
        raise
    removed = remove_shortcuts(previous, keep=created)
    start_link = sync_start_link(s, app_id)
    write_created_shortcuts(created + leftover_shortcuts(previous, removed + created), start_link)
    from pyapp.DONT_CHANGE.scripts.desktop.batch_shortcuts import sync

    batches = sync(s, app_id, Path(SHORTCUT_OUTPUT_DIR))
    if batches:
        print_success(f"Created {len(batches)} batch entry points in batch_shortcuts.")
    for path in removed:
        print(f"  {styled('-', ANSI_DIM)} {styled('removed ' + _short(path), ANSI_DIM)}")
    if s.browser_terminal_shortcut_name:
        from pyapp.DONT_CHANGE.scripts.browser_links import page_url

        print_heading("Browser terminal")
        print(f"  bookmark    {page_url(s, app_id)}  {styled('(while running)', ANSI_DIM)}")
        if start_link:
            print(f"  start link  {start_link}://start")
    delete_finished_run_folders()
    from pyapp.DONT_CHANGE.scripts.github.update_check import tell_about_update

    tell_about_update(s.check_for_launcher_updates)
    from pyapp.DONT_CHANGE.scripts.hidden_caches import hide_cache_folders

    hide_cache_folders()
    print()
    print_success(" Setup completed. ")

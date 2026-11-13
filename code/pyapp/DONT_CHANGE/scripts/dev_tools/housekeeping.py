"""Dev tools for housekeeping: delete logs, remove shortcuts, show status."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple, Union

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import (
    all_packages,
    describe_python_request,
    display_path,
    package_entries,
    requirements_file_entries,
    requirements_file_path,
    settings,
    validate,
)
from pyapp.DONT_CHANGE.scripts.console_tools import (
    ask,
    print_choices,
    print_fields,
    print_heading,
    print_info,
    print_success,
    print_warn,
)
from pyapp.DONT_CHANGE.scripts.dev_tools.common import confirm
from pyapp.DONT_CHANGE.scripts.diagnostics import diagnostics_summary, note_ignored
from pyapp.DONT_CHANGE.scripts.env.pyproject import current_requires_python, declared_dependencies
from pyapp.DONT_CHANGE.scripts.env.pythons import read_python_version_file, version_text
from pyapp.DONT_CHANGE.scripts.env.uv import uv_exe, uv_succeeds, uv_version
from pyapp.DONT_CHANGE.scripts.env.venv import read_venv_config, venv_home_valid, venv_version
from pyapp.DONT_CHANGE.scripts.errors import SettingsError, SetupError
from pyapp.DONT_CHANGE.scripts.runtime_state import ProcessRegistry


def _size_text(files: List[Path]) -> str:
    """e.g. "12 file(s), 3.4 MB"."""
    if not files:
        return "empty"
    return f"{len(files)} file(s), {sum(path.stat().st_size for path in files) / 1_048_576:.1f} MB"


def _folder_contents(folder: Optional[str]) -> str:
    """What cleaning a whole folder would delete."""
    if not folder or not Path(folder).is_dir():
        return "empty"
    return _size_text([path for path in Path(folder).rglob("*") if path.is_file() and path.name != ".gitkeep"])


def _log_name_pattern(configured: str) -> Pattern[str]:
    """Names the launcher gives the logs of a configured log_path.

    A log is named after the configured file name with its date placeholders filled in, then
    "_" + the 12 hex digits of its run (runtime_state.unique_log_path), optionally followed by the
    raw-output suffix. Matching this shape keeps Clean away from other files in a shared folder.
    """
    from pyapp.DONT_CHANGE.scripts.launcher_ui import OUTPUT_LOG_SUFFIX

    template = Path(configured).name
    stem, extension = Path(template).stem, Path(template).suffix

    def to_regex(text: str) -> str:
        parts = re.split(r"(%.)", text)
        return "".join(
            "%" if part == "%%" else r"[^\\/]+?" if len(part) == 2 and part[0] == "%" else re.escape(part)
            for part in parts
        )

    output_suffix = re.escape(OUTPUT_LOG_SUFFIX)
    pattern = f"{to_regex(stem)}_[0-9a-f]{{12}}{to_regex(extension)}(?:{output_suffix})?"
    return re.compile(pattern, re.IGNORECASE)


def _owned_logs(folder: Optional[str], configured: Optional[str]) -> List[Path]:
    """The launcher's own log files directly in a log folder; other files are never included."""
    if not folder or not configured or not Path(folder).is_dir():
        return []
    pattern = _log_name_pattern(configured)
    return [path for path in Path(folder).iterdir() if path.is_file() and pattern.fullmatch(path.name)]


def cmd_clean(_arguments: List[str]) -> None:
    """Delete logs or run diagnostics."""
    from pyapp.DONT_CHANGE.scripts.file_tools import remove_tree_inside
    from pyapp.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

    s = settings()
    log_folder = get_log_folder_path(s.log_path, s.log_path_is_relative_to_start_folder_if_relative)
    crash_folder = get_log_folder_path(s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative)
    owned = {"logs": _owned_logs(log_folder, s.log_path), "crash": _owned_logs(crash_folder, s.crash_log_path)}
    options = [
        (
            "logs",
            f"Log files in {display_path(log_folder)}: {_size_text(owned['logs'])}"
            if log_folder
            else "Log files: disabled",
        ),
        (
            "crash",
            f"Crash logs in {display_path(crash_folder)}: {_size_text(owned['crash'])}"
            if crash_folder
            else "Crash logs: disabled",
        ),
        ("runs", f"Per-run diagnostics in tmp/runs: {_folder_contents(paths.RUNS_DIR)}"),
    ]
    print_heading("Clean")
    print_choices(label for _, label in options)
    chosen = ask("Numbers to clean (space separated), Enter = cancel:").replace(",", " ").split()
    keys = {options[int(c) - 1][0] for c in chosen if c.isdecimal() and 1 <= int(c) <= len(options)}
    if not keys or not confirm("Delete permanently?"):
        print_info("Nothing was deleted.")
        return
    in_use = 0
    deleted = 0
    # A set, because both log kinds may share one folder and name pattern.
    for path in {path for key in ("logs", "crash") if key in keys for path in owned[key]}:
        try:
            path.unlink()
            deleted += 1
        except FileNotFoundError:
            pass
        except PermissionError:  # the log of an instance that is still running
            in_use += 1
    if in_use:
        print_warn(f"Kept {in_use} file(s) that are in use, e.g. by a running instance.")
    runs_deleted = False
    if "runs" in keys and Path(paths.RUNS_DIR).is_dir():
        # A running instance still writes its completion report into its run folder.
        if ProcessRegistry(paths.PROCESS_REGISTRY_DIR).records()[0]:
            print_warn("Kept the per-run diagnostics: close the running app instance(s) first.")
        else:
            remove_tree_inside(paths.RUNS_DIR, paths.TEMPORARY_DIR)
            runs_deleted = True
    runs = " and the per-run diagnostics" if runs_deleted else ""
    print_success(f"Deleted {deleted} log file(s){runs}.")


def cmd_remove_shortcuts(_arguments: List[str]) -> None:
    """Remove every shortcut Setup created (project folder, Start Menu, Desktop)."""
    from pyapp.DONT_CHANGE.scripts.browser_links import unregister_start_link
    from pyapp.DONT_CHANGE.scripts.shortcuts import (
        leftover_shortcuts,
        read_created_shortcuts,
        read_start_link,
        remove_shortcuts,
        write_created_shortcuts,
    )

    previous = read_created_shortcuts()
    removed = remove_shortcuts(previous)
    start_link = read_start_link()
    if start_link and unregister_start_link(start_link):
        print_info(f"Removed the start link {start_link}://")
    # Shortcuts that could not be deleted (e.g. open in Explorer) stay recorded for the next try.
    write_created_shortcuts(leftover_shortcuts(previous, removed))
    for path in removed:
        print_info("Removed: " + path)
    print_success(f"Removed {len(removed)} shortcut(s). Run Setup to create them again.")


def cmd_status(_arguments: List[str]) -> None:
    """Show uv, Python, environment and shortcut state."""
    s = settings()
    try:
        validate(s)
        settings_state = "valid"
    except SettingsError as error:
        settings_state = str(error)
    try:
        uv = uv_exe()
        where = {
            os.path.normcase(paths.LOCAL_UV_EXE): " (local)",
            os.path.normcase(paths.SHARED_UV_EXE): " (shared by PyApp projects of this user)",
        }.get(os.path.normcase(os.path.normpath(uv)), " (global)")
        uv_state = f"{uv_version()} at {uv}{where}"
    except SetupError:
        uv = None
        uv_state = "missing (Setup or the next start installs it)"
    config = read_venv_config()
    lock_state: Tuple[str, bool] = ("(missing - created on the next start)", False)
    if Path(paths.UV_LOCK_PATH).is_file() and uv is None:
        lock_state = ("present (not checked: uv is missing)", False)
    elif Path(paths.UV_LOCK_PATH).is_file():
        up_to_date = uv_succeeds(["lock", "--check", "--offline"])
        lock_state = ("up to date", True) if up_to_date else ("needs an update (next start or sync)", False)
    try:
        from pyapp.DONT_CHANGE.scripts.shortcuts import read_created_shortcuts

        shortcut_count = f"{len(read_created_shortcuts())} created by Setup"
    except Exception:
        note_ignored("cmd_status: shortcut list")
        shortcut_count = "?"
    from pyapp.DONT_CHANGE.scripts.dev_tools.self_contained import is_self_contained

    self_contained = (
        "yes (uv, Python and packages are inside the folder)"
        if is_self_contained(s)
        else "no (uses the shared uv and Python; make_self_contained changes that)"
    )
    ignored = diagnostics_summary()
    # status is what the README says to run when something is wrong: a requirements_path file
    # that cannot be read is shown in its row (and under Settings), not raised.
    try:
        from_file: Optional[List[str]] = requirements_file_entries(s)
        in_sync = declared_dependencies() == all_packages(s)
        file_problem = ""
    except SettingsError as error:
        from_file, in_sync, file_problem = None, False, str(error)
    sections: Dict[str, List[Union[Tuple[str, object], Tuple[str, object, bool]]]] = {
        "Project": [
            ("Program", s.program_name),
            ("Launcher version", paths.LAUNCHER_VERSION),
            ("Settings", settings_state, settings_state == "valid"),
            ("Shortcuts", shortcut_count),
            ("Self-contained", self_contained),
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
            (".python-version", read_python_version_file() or "(missing)"),
            ("requires-python", current_requires_python() or "(missing)"),
        ],
        "Packages": [
            ("packages", ", ".join(package_entries(s)) or "(none)"),
            (
                "requirements_path",
                file_problem
                or (
                    f"{display_path(requirements_file_path(s) or '')}: {', '.join(from_file or []) or '(none)'}"
                    if requirements_file_path(s)
                    else "(none)"
                ),
                not file_problem,
            ),
            (
                "pyproject.toml",
                "matches developer_settings.py" if in_sync else "differs (updated on the next start or dev tool)",
                in_sync,
            ),
            ("uv.lock", lock_state[0], lock_state[1]),
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
    problems = [row[0] for rows in sections.values() for row in rows if len(row) == 3 and not row[2]]
    print()
    if problems:
        print_warn("Needs attention: " + ", ".join(problems))
    else:
        print_success("Everything looks fine.")


def cmd_test(arguments: List[str]) -> None:
    """Run the launcher's regression tests (DONT_CHANGE/tests); optional groups or file patterns."""
    import subprocess

    script = str(Path(paths.DONT_CHANGE_DIR) / "tests" / "src" / "run_regressions.py")
    if not Path(script).is_file():
        print_info("The tests folder DONT_CHANGE/tests was removed; nothing to run.")
        return
    print_heading("Launcher tests")
    # Run this checkout's test runner with the current Python interpreter.
    code = subprocess.run([sys.executable, "-B", script, "-q", *arguments], check=False).returncode  # noqa: S603
    print()
    if code:
        raise SetupError("Some launcher tests failed (see above).")
    print_success("All launcher tests passed.")

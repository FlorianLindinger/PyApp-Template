# ruff: noqa: E402
# Bootstrap path setup must run before importing project modules.

"""Launcher appearance, log-path policy and process-registry compatibility helpers."""

# =========================

import os
import sys

# =========================
# add root dir for debug cases where this script is called on its own:
ROOT_DIR: str = os.path.normpath(os.path.dirname(__file__) + "\\..\\..\\..")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
# =========================

from backend.developer_settings import (
    program_name,
    terminal_bg_color,
    terminal_text_color,
)
from backend.DONT_CHANGE.scripts.console_tools import (
    print_warn,
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
)
from backend.DONT_CHANGE.scripts.console_tools import (
    set_terminal_colors as _set_terminal_colors,
)
from backend.DONT_CHANGE.scripts.filesystem_tools import (
    set_hidden_in_explorer as _set_hidden_in_explorer,
)
from backend.DONT_CHANGE.settings.backend_settings import (
    DEV_SETTINGS_DIR,
    EMPTY_ARG_INDICATOR,
    FOLDERS_TO_MAKE_HIDDEN_IN_SHORTCUT_AND_ROOT_FOLDERS,
    ICON_PATH,
    SHORTCUT_OUTPUT_DIR,
)

_TERMINAL_APPEARANCE_WAS_SET: bool = False

TERMINAL_COLORS: str = ""
if terminal_bg_color:
    TERMINAL_COLORS += terminal_bg_color
if terminal_text_color:
    TERMINAL_COLORS += terminal_text_color

# =========================
# miscellaneous functions


def set_hidden_in_explorer() -> None:
    """Apply the configured hidden attribute in the project root and its parent."""
    _set_hidden_in_explorer(
        [
            os.path.join(base_dir, path)
            for base_dir in (ROOT_DIR, SHORTCUT_OUTPUT_DIR)
            for path in FOLDERS_TO_MAKE_HIDDEN_IN_SHORTCUT_AND_ROOT_FOLDERS
        ]
    )


def do_stuff_when_not_normal_start():
    """Apply the configured Explorer hidden attributes for a non-application action."""
    set_hidden_in_explorer()


def make_empty_args_safe(args: list[str | None]) -> list[str]:
    """Needed because passing empty args as "" in Windows can be flimsy -> replace "" with EMPTY_ARG_INDICATOR and decode in child.

    None get conveted to EMPTY_ARG_INDICATOR as well."""
    return [a if a not in ("", None) else EMPTY_ARG_INDICATOR for a in args]


def print_traceback(message: str = "") -> None:
    """Print a colored traceback and optionally wait for the user before the terminal closes."""

    # `rich` is installed into the managed backend Python, not this analyzer's environment.
    from rich.console import Console
    from rich.traceback import Traceback

    console = Console()

    exc_type, exc_value, traceback_ = sys.exc_info()

    print()
    print()
    print_warn("=" * 30)

    if message:
        print_warn(message)
        print("-" * 30)

    if exc_type is not None and exc_value is not None:
        console.print(
            Traceback.from_exception(exc_type, exc_value, traceback_, show_locals=False)
        )

    print_warn("=" * 30)


def set_terminal_appearance_once(app_id: str) -> None:
    """Apply terminal title, AppID, and icon once per process."""
    global _TERMINAL_APPEARANCE_WAS_SET

    if not _TERMINAL_APPEARANCE_WAS_SET:
        set_terminal_title(program_name)
        set_terminal_icon(ICON_PATH)

        if app_id:
            set_terminal_app_id(app_id)

        _TERMINAL_APPEARANCE_WAS_SET = True


def set_terminal_colors(colors: str | None = TERMINAL_COLORS) -> None:
    """Apply a Windows console color code, or leave colors unchanged for ``None``."""
    _set_terminal_colors(colors=colors)


def get_log_folder_path(
    log_path: str | bool | None, is_relative_to_start_folder_if_relative: bool
) -> str | None:
    """Converts log_path = None, False, "" to None. Converts datetime format. Converts relative path either relative to developer_settings.py or start folder (where the start shortcut is)."""

    assert log_path is not True, (
        "True is not a valid value for the log path. Choose: (relative) path, None, or False."
    )
    if log_path:
        if not os.path.isabs(log_path):
            if is_relative_to_start_folder_if_relative:
                log_path_resolved = os.path.normpath(
                    os.path.join(
                        os.environ.get("PYAPP_START_DIR", os.getcwd()), log_path
                    )
                )
            else:
                log_path_resolved = os.path.normpath(
                    os.path.join(DEV_SETTINGS_DIR, log_path)
                )
        else:
            log_path_resolved = log_path

        log_folder_path_resolved = os.path.dirname(log_path_resolved)

        if "%" in log_folder_path_resolved:
            from datetime import datetime

            log_folder_path_resolved = (
                datetime.now().astimezone().strftime(log_folder_path_resolved)
            )

        return log_folder_path_resolved
    else:
        return None


def get_log_path(
    log_path: str | bool | None, is_relative_to_start_folder_if_relative: bool
) -> str:
    """Handles log paths: Converts None and False to "". Converts datetime format. Converts relative path either relative to developer_settings.py or start folder (where the start shortcut is)."""

    assert log_path is not True, (
        "True is not a valid value for the log path. Choose: (relative) path, None, or False."
    )
    if log_path:
        if not os.path.isabs(log_path):
            if is_relative_to_start_folder_if_relative:
                log_path_resolved = os.path.normpath(
                    os.path.join(
                        os.environ.get("PYAPP_START_DIR", os.getcwd()), log_path
                    )
                )
            else:
                log_path_resolved = os.path.normpath(
                    os.path.join(DEV_SETTINGS_DIR, log_path)
                )
        else:
            log_path_resolved = log_path

        if "%" in log_path_resolved:
            from datetime import datetime

            log_path_resolved = datetime.now().astimezone().strftime(log_path_resolved)

        return log_path_resolved
    else:
        return ""


def get_running_processes_from_pid_file(pid_path: str) -> tuple[list[int], int]:
    """Return verified running launcher PIDs and the count of removed stale registry entries."""
    from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    registry = ProcessRegistry(pid_path)
    with registry.lock():
        records, stale = registry.records()
        return [record["pid"] for record in records], stale


def stop_processes_from_pid_file(pid_path: str) -> tuple[int, int, list[str]]:
    """Stop verified application process trees and return stopped, stale and failure details."""
    from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    return ProcessRegistry(pid_path).stop()

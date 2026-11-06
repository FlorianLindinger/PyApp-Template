"""Launcher appearance, error printing, log paths and log retention."""

from __future__ import annotations

import os
import sys
import time

from backend.DONT_CHANGE.backend_settings import (
    DEV_SETTINGS_DIR,
    FOLDERS_TO_MAKE_HIDDEN_IN_SHORTCUT_AND_ROOT_FOLDERS,
    ICON_PATH,
    PROCESS_REGISTRY_DIR,
    PYTHON_SCRIPTS_DIR,
    RUNS_DIR,
    SHORTCUT_OUTPUT_DIR,
)
from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.console_tools import (
    enable_ansi,
    print_warn,
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
)
from backend.DONT_CHANGE.scripts.console_tools import (
    set_terminal_colors as _set_terminal_colors,
)
from backend.DONT_CHANGE.scripts.diagnostics import note_ignored
from backend.DONT_CHANGE.scripts.filesystem_tools import (
    set_hidden_in_explorer as _set_hidden_in_explorer,
)

_TERMINAL_APPEARANCE_WAS_SET = False
# Raw-output companion of each log file (written by the watchdog as log_path + this suffix).
OUTPUT_LOG_SUFFIX = ".output.log"
_SETTINGS_COLORS = object()  # default of set_terminal_colors: the colors from developer_settings.py


def set_hidden_in_explorer() -> None:
    """Apply the configured hidden attribute in the project root and the code folder."""
    _set_hidden_in_explorer(
        [
            os.path.join(base_dir, path)
            for base_dir in (PYTHON_SCRIPTS_DIR, SHORTCUT_OUTPUT_DIR)
            for path in FOLDERS_TO_MAKE_HIDDEN_IN_SHORTCUT_AND_ROOT_FOLDERS
        ]
    )


def print_traceback(message: str = "") -> None:
    """Print the current exception (standard library formatting) framed by a message."""
    import traceback

    enable_ansi()
    print()
    print_warn("=" * 30)
    if message:
        print_warn(message)
        print("-" * 30)
    if sys.exc_info()[0] is not None:
        print(traceback.format_exc().rstrip())
    print_warn("=" * 30)


def set_terminal_appearance_once(app_id: str) -> None:
    """Apply terminal title, AppID, and icon once per process."""
    global _TERMINAL_APPEARANCE_WAS_SET
    if not _TERMINAL_APPEARANCE_WAS_SET:
        set_terminal_title(settings().program_name)
        set_terminal_icon(ICON_PATH)
        if app_id:
            set_terminal_app_id(app_id)
        _TERMINAL_APPEARANCE_WAS_SET = True


def set_terminal_colors(colors=_SETTINGS_COLORS) -> None:
    """Apply a Windows console color code ("9F"); None or "" leaves the colors unchanged.

    Without an argument: terminal_bg_color + terminal_text_color from developer_settings.py.
    """
    if colors is _SETTINGS_COLORS:
        s = settings()
        colors = (s.terminal_bg_color or "") + (s.terminal_text_color or "")
    _set_terminal_colors(colors=colors)


def get_log_path(log_path, is_relative_to_start_folder_if_relative: bool) -> str:
    """Resolve a configured log path ("" when disabled).

    Date placeholders are filled in the configured text only, so a "%" in the
    project folder's own path is never interpreted.
    """
    if not log_path:
        return ""
    from datetime import datetime

    configured = datetime.now().strftime(log_path) if "%" in log_path else log_path
    if os.path.isabs(configured):
        return os.path.normpath(configured)
    base = os.environ.get("PYAPP_START_DIR", os.getcwd()) if is_relative_to_start_folder_if_relative else DEV_SETTINGS_DIR
    return os.path.normpath(os.path.join(base, configured))


def get_log_folder_path(log_path, is_relative_to_start_folder_if_relative: bool) -> str | None:
    """Folder of the resolved log path, or None when logging is disabled."""
    resolved = get_log_path(log_path, is_relative_to_start_folder_if_relative)
    return os.path.dirname(resolved) if resolved else None


def prune_logs(s) -> None:
    """Apply max_log_files and max_run_folder_age_days (best effort, never raises)."""
    import shutil

    try:
        for path_setting, relative_setting in (
            ("log_path", "log_path_is_relative_to_start_folder_if_relative"),
            ("crash_log_path", "crash_log_path_is_relative_to_start_folder_if_relative"),
        ):
            pattern = getattr(s, path_setting)
            if not pattern or not s.max_log_files:
                continue
            folder = get_log_folder_path(pattern, getattr(s, relative_setting))
            prefix = os.path.basename(pattern).split("%", 1)[0]
            if not folder or not os.path.isdir(folder) or not prefix:
                continue
            # One run = one log; its raw-output companion (OUTPUT_LOG_SUFFIX) counts with it.
            files = [
                os.path.join(folder, name)
                for name in os.listdir(folder)
                if name.startswith(prefix)
                and not name.endswith(OUTPUT_LOG_SUFFIX)
                and os.path.isfile(os.path.join(folder, name))
            ]
            files.sort(key=os.path.getmtime, reverse=True)
            for old in files[s.max_log_files :]:
                for path in (old, old + OUTPUT_LOG_SUFFIX):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        if s.max_run_folder_age_days and os.path.isdir(RUNS_DIR):
            limit = time.time() - s.max_run_folder_age_days * 86400
            for name in os.listdir(RUNS_DIR):
                path = os.path.join(RUNS_DIR, name)
                if os.path.isdir(path) and os.path.getmtime(path) < limit:
                    shutil.rmtree(path, ignore_errors=True)
    except Exception:
        note_ignored("prune_logs")


def stop_running_instances(timeout: float = 0.0, report=None):
    """Stop verified application instances (graceful first, see ProcessRegistry.stop)."""
    from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    return ProcessRegistry(PROCESS_REGISTRY_DIR).stop(timeout, report)

"""Launcher appearance, error printing and log paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional

from backend.DONT_CHANGE.backend_settings import (
    DEV_SETTINGS_DIR,
    ICON_PATH,
    PROCESS_REGISTRY_DIR,
    RUNS_DIR,
)
from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    enable_ansi,
    print_error,
    set_terminal_app_id,
    set_terminal_icon,
    set_terminal_title,
    styled,
)
from backend.DONT_CHANGE.scripts.console_tools import (
    set_terminal_colors as _set_terminal_colors,
)
from backend.DONT_CHANGE.scripts.diagnostics import note_ignored
from backend.DONT_CHANGE.scripts.file_tools import (
    remove_tree_inside,
)

_TERMINAL_APPEARANCE_WAS_SET = False
# Raw-output companion of each log file (written by the watchdog as log_path + this suffix).
OUTPUT_LOG_SUFFIX = ".output.log"
# A run that is starting or has just ended is not registered as running but still uses its folder.
RUN_FOLDER_IN_USE_SECONDS = 300


def print_traceback(message: str = "") -> None:
    """Print the current exception (standard library formatting) framed by a message."""
    import traceback

    enable_ansi()
    print()
    if message:
        print_error(message)
    if sys.exc_info()[0] is not None:
        print(styled(traceback.format_exc().rstrip(), ANSI_DIM))


def set_terminal_appearance_once(app_id: str) -> None:
    """Apply terminal title, AppID, and icon once per process."""
    global _TERMINAL_APPEARANCE_WAS_SET
    if not _TERMINAL_APPEARANCE_WAS_SET:
        set_terminal_title(settings().program_name)
        set_terminal_icon(ICON_PATH)
        if app_id:
            set_terminal_app_id(app_id)
        _TERMINAL_APPEARANCE_WAS_SET = True


def set_settings_colors() -> None:
    """Apply terminal_bg_color + terminal_text_color from developer_settings.py (both empty: unchanged)."""
    s = settings()
    _set_terminal_colors((s.terminal_bg_color or "") + (s.terminal_text_color or ""))


def get_log_path(log_path: Optional[str], is_relative_to_start_folder_if_relative: bool) -> str:
    """Resolve a configured log path ("" when disabled).

    Date placeholders are filled in the configured text only, so a "%" in the
    project folder's own path is never interpreted.
    """
    if not log_path:
        return ""
    from datetime import datetime

    configured = datetime.now().astimezone().strftime(log_path) if "%" in log_path else log_path
    # Keep os.path.isabs: rooted Windows paths have different pathlib semantics on Python 3.8-3.12.
    if os.path.isabs(configured):  # noqa: PTH117
        return os.path.normpath(configured)
    base = (
        os.environ.get("PYAPP_START_DIR", str(Path.cwd()))
        if is_relative_to_start_folder_if_relative
        else DEV_SETTINGS_DIR
    )
    return os.path.normpath(str(Path(base) / configured))


def get_log_folder_path(log_path: Optional[str], is_relative_to_start_folder_if_relative: bool) -> Optional[str]:
    """Folder of the resolved log path, or None when logging is disabled."""
    resolved = get_log_path(log_path, is_relative_to_start_folder_if_relative)
    return str(Path(resolved).parent) if resolved else None


def stop_running_instances(timeout: float = 0.0, report: Optional[Callable[[str], object]] = None):
    """Stop verified application instances (graceful first, see ProcessRegistry.stop)."""
    from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    return ProcessRegistry(PROCESS_REGISTRY_DIR).stop(timeout, report)


def delete_finished_run_folders() -> None:
    """Delete the run folders when no instance is running; housekeeping that never stops a launch."""
    import time

    from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry

    try:
        if not Path(RUNS_DIR).is_dir() or ProcessRegistry(PROCESS_REGISTRY_DIR).records()[0]:
            return
        newest_allowed = time.time() - RUN_FOLDER_IN_USE_SECONDS
        with os.scandir(RUNS_DIR) as entries:
            folders = [
                e.path for e in entries if e.is_dir(follow_symlinks=False) and e.stat().st_mtime < newest_allowed
            ]
        for folder in folders:
            try:
                remove_tree_inside(folder, RUNS_DIR)
            except OSError:
                pass  # e.g. a file is open in an editor: tried again next time
    except Exception:
        note_ignored("delete_finished_run_folders")

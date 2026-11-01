"""Open the folder containing the configured crash log."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to open crash-log folder: {e}"
close_terminal_on_finish: bool = True
import os
import sys

from backend.developer_settings import (
    crash_log_path,
    crash_log_path_is_relative_to_start_folder_if_relative,
)
from backend.DONT_CHANGE.scripts.console_tools import (
    enable_unminimize_and_foreground_terminal_on_first_print,
    print_warn,
)
from backend.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path, set_terminal_colors
from backend.DONT_CHANGE.settings.backend_settings import DEV_SETTINGS_PATH


def main() -> None:
    """Open the configured crash-log folder, if one is enabled."""
    set_terminal_colors()
    enable_unminimize_and_foreground_terminal_on_first_print()
    folder_path = get_log_folder_path(crash_log_path, crash_log_path_is_relative_to_start_folder_if_relative)
    if folder_path is None:
        print_warn(
            f'''[Info] Can't open crash-log folder because crash_log_path is disabled in "{DEV_SETTINGS_PATH}".'''
        )
    elif not os.path.exists(folder_path):
        print_warn(f'[Error] Crash-log folder ("{folder_path}") does not exist.')
    else:
        os.startfile(folder_path)

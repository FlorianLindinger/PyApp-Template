# ruff: noqa: E402
# The early __main__ handoff lets the shared runner catch dependency import failures.

"""Open the configured user settings file."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to open settings file: {e}"
close_terminal_on_finish: bool = True
import os
import sys

from backend.developer_settings import user_settings_path
from backend.DONT_CHANGE.scripts.console_tools import (
    enable_unminimize_and_foreground_terminal_on_first_print,
    print_warn,
)
from backend.DONT_CHANGE.scripts.filesystem_tools import make_abs_path_relative_to_file
from backend.DONT_CHANGE.scripts.launcher_ui import set_terminal_colors
from backend.DONT_CHANGE.scripts.shell_tools import open_in_editor
from backend.DONT_CHANGE.settings.backend_settings import DEV_SETTINGS_PATH


def main() -> None:
    """Open the optional settings file after resolving its configured path."""
    set_terminal_colors()
    enable_unminimize_and_foreground_terminal_on_first_print()
    if not user_settings_path:
        print_warn(
            f'''[Info] Can't open settings file because user_settings_path is disabled in "{DEV_SETTINGS_PATH}".'''
        )
        return
    path = make_abs_path_relative_to_file(user_settings_path, DEV_SETTINGS_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    open_in_editor(path)

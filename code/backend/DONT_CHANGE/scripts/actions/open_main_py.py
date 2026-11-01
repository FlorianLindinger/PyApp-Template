# ruff: noqa: E402
# The early __main__ handoff lets the shared runner catch dependency import failures.

"""Open the project's main.py file in the configured editor."""

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

fail_message: str = "[Error] Failed to open main.py file: {e}"
close_terminal_on_finish: bool = True
import os
import sys

from backend.DONT_CHANGE.scripts.console_tools import (
    enable_unminimize_and_foreground_terminal_on_first_print,
    print_warn,
)
from backend.DONT_CHANGE.scripts.launcher_ui import set_terminal_colors
from backend.DONT_CHANGE.scripts.shell_tools import open_in_editor
from backend.DONT_CHANGE.settings.backend_settings import MAIN_PY_SCRIPT_PATH


def main() -> None:
    """Open main.py or explain why it cannot be opened."""
    set_terminal_colors()
    enable_unminimize_and_foreground_terminal_on_first_print()
    if not os.path.exists(MAIN_PY_SCRIPT_PATH):
        print_warn(f'[Error] main.py file ("{MAIN_PY_SCRIPT_PATH}") does not exist.')
        return
    open_in_editor(MAIN_PY_SCRIPT_PATH)

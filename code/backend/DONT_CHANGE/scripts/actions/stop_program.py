"""Stop running PyApp Template program instances recorded in the PID file."""

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message: str = "[Error] Failed to stop process: {e}"
close_terminal_on_finish: bool = True
close_countdown_on_success_s: int = 3
close_countdown_when_no_pid_file_s: int = 5
import sys
import time

from backend.DONT_CHANGE.scripts.console_tools import (
    enable_unminimize_and_foreground_terminal_on_first_print,
    print_success,
)
from backend.DONT_CHANGE.scripts.filesystem_tools import make_abs_path_relative_to_file
from backend.DONT_CHANGE.scripts.launcher_ui import set_terminal_colors, stop_processes_from_pid_file
from backend.DONT_CHANGE.settings.backend_settings import (
    DEV_SETTINGS_PATH,
    PROCESS_ID_FILE_PATH,
)


def print_close_countdown(seconds: int) -> None:
    """Print a countdown before the terminal closes automatically."""
    print("[Info] Closing in:")
    for seconds_remaining in range(seconds, 0, -1):
        print(seconds_remaining)
        time.sleep(1)


def main() -> None:
    """Stop live processes and remove stale entries from the PID file."""
    set_terminal_colors()
    enable_unminimize_and_foreground_terminal_on_first_print()
    pid_path = make_abs_path_relative_to_file(PROCESS_ID_FILE_PATH, DEV_SETTINGS_PATH)
    stopped_count, stale_count, failed_messages = stop_processes_from_pid_file(pid_path)
    if failed_messages:
        raise RuntimeError("Failed to stop these PID(s):\n" + "\n".join(failed_messages))
    if stopped_count == 0:
        if stale_count == 0:
            print(f'[Info] No PID file found at "{pid_path}".')
            print("This could mean it was already stopped via this script.")
            print_close_countdown(close_countdown_when_no_pid_file_s)
        else:
            print(f"[Info] Nothing to stop. Removed {stale_count} stale PID entries from {pid_path}.")
        return
    print_success(f"[Success] Stopped {stopped_count} process(es).")
    if stale_count:
        print_success(f"[Info] Removed {stale_count} stale PID entries.")
    print_close_countdown(close_countdown_on_success_s)

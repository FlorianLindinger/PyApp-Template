"""Stop the running instances of the app (asks them to close first, see stop_timeout_seconds)."""

from __future__ import annotations

fail_message: str = "[Error] Failed to stop process: {e}"
close_countdown_on_success_s: int = 3
close_countdown_when_nothing_runs_s: int = 5
import time

from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.console_tools import (
    enable_unminimize_and_foreground_terminal_on_first_print,
    print_success,
)
from backend.DONT_CHANGE.scripts.launcher_ui import (
    set_settings_colors,
    stop_running_instances,
)


def print_close_countdown(seconds: int) -> None:
    """Print a countdown before the terminal closes automatically."""
    print("[Info] Closing in:")
    for seconds_remaining in range(seconds, 0, -1):
        print(seconds_remaining)
        time.sleep(1)


def main() -> None:
    """Ask running instances to close, terminate those that do not, and drop stale records."""
    s = settings()
    set_settings_colors()
    enable_unminimize_and_foreground_terminal_on_first_print()
    stopped_count, stale_count, failed_messages = stop_running_instances(s.stop_timeout_seconds, report=print)
    if failed_messages:
        raise RuntimeError("Failed to stop these instance(s):\n" + "\n".join(failed_messages))
    if stale_count:
        print(f"[Info] Removed {stale_count} record(s) of instances that had already ended.")
    if stopped_count == 0:
        print(f"[Info] {s.program_name} is not running.")
        print_close_countdown(close_countdown_when_nothing_runs_s)
        return
    print_success(f"[Success] Stopped {stopped_count} instance(s) of {s.program_name}.")
    print_close_countdown(close_countdown_on_success_s)

"""Stop the running instances of the app (asks them to close first, see stop_timeout_seconds)."""

from __future__ import annotations

fail_message: str = "Failed to stop process: {e}"
close_countdown_on_success_s: int = 3
close_countdown_when_nothing_runs_s: int = 5
import time

from backend.DONT_CHANGE.scripts.config import settings
from backend.DONT_CHANGE.scripts.console_tools import (
    ANSI_DIM,
    enable_unminimize_and_foreground_terminal_on_first_print,
    print_info,
    print_success,
    styled,
)
from backend.DONT_CHANGE.scripts.launcher_ui import (
    stop_running_instances,
)


def print_close_countdown(seconds: int) -> None:
    """Print a countdown before the terminal closes automatically."""
    for seconds_remaining in range(seconds, 0, -1):
        print("\r" + styled(f"This window closes in {seconds_remaining} s ...", ANSI_DIM), end="", flush=True)
        time.sleep(1)
    print()


def main() -> None:
    """Ask running instances to close, terminate those that do not, and drop stale records."""
    s = settings()
    enable_unminimize_and_foreground_terminal_on_first_print()
    stopped_count, stale_count, failed_messages = stop_running_instances(s.stop_timeout_seconds, report=print_info)
    if failed_messages:
        raise RuntimeError("Failed to stop these instance(s):\n" + "\n".join(failed_messages))
    if stale_count:
        print_info(f"Removed {stale_count} record(s) of instances that had already ended.")
    if stopped_count == 0:
        print_info(f"{s.program_name} is not running.")
        print_close_countdown(close_countdown_when_nothing_runs_s)
        return
    print_success(f"Stopped {stopped_count} instance(s) of {s.program_name}.")
    print_close_countdown(close_countdown_on_success_s)

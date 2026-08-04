"""Stop running PyApp Template program instances recorded in the PID file."""

# ==============================
# settings

fail_message: str = "[Error] Failed to stop process: {e}"
close_terminal_on_finish: bool = True
close_countdown_on_success_s: int = 3
close_countdown_when_no_pid_file_s: int = 5

import os

root_dir: str = os.path.dirname(__file__) + "\\..\\..\\..\\.."

# ==============================

try:
    # ==============================
    # import Python packages

    import sys
    import time

    # ==============================
    # import third-party packages

    # ==============================
    # import from files

    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from backend.DONT_CHANGE.scripts.common_code import (
        input_warn,
        print_traceback,
        set_terminal_colors,
        stop_processes_from_pid_file,
    )
    from backend.DONT_CHANGE.scripts.generic_helpers import (
        close_terminal,
        enable_unminimize_and_foreground_terminal_on_first_print,
        make_abs_path_relative_to_file,
        print_success,
    )
    from backend.DONT_CHANGE.settings.backend_settings import DEV_SETTINGS_PATH, PROCESS_ID_FILE_PATH

    # ==============================
    # local variables

    # ==============================
    # local functions/classes

    def print_close_countdown(seconds: int) -> None:
        """Print a countdown before the terminal closes automatically."""
        print("[Info] Closing in:")
        for seconds_remaining in range(seconds, 0, -1):
            print(seconds_remaining)
            time.sleep(1)

    # ==============================
    # main function

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
                input("Press enter to exit")
            return

        print_success(f"[Success] Stopped {stopped_count} process(es).")
        if stale_count:
            print_success(f"[Info] Removed {stale_count} stale PID entries.")
        print_close_countdown(close_countdown_on_success_s)

    # ==============================
    # execute main function

    if __name__ == "__main__":
        try:
            main()
        except Exception as e:
            print_traceback(fail_message.format(e=e))
            input_warn("[Error] Press enter to exit")
        if close_terminal_on_finish:
            close_terminal()

except Exception as e:
    import traceback

    print()
    print()
    print("=" * 30)
    print(fail_message.format(e=e))
    print("-" * 30)
    print(traceback.format_exc())
    print("=" * 30)
    input("[Error] Press enter to exit")
    if close_terminal_on_finish:
        os._exit(1)

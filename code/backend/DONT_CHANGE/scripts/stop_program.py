"""Stop running PyApp Template program instances recorded in the PID file."""

# ==========================================================================
# local settings

sleep_before_close_on_success_s = 2

# ==========================================================================
# package imports

import os
import sys
import time

# ==========================================================================
# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# ==========================================================================
# import from common variables and developer settings
from backend.DONT_CHANGE.scripts._common_code import (
    close_terminal,
    make_abs_path_relative_to_file,
    print_success,
    print_traceback,
    # setup_terminal_colors_and_unminimize_plus_foreground_on_first_print,
    stop_processes_from_pid_file,
)
from backend.DONT_CHANGE.scripts._common_variables import developer_settings_path, process_id_file_path

# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(process_id_file_path, developer_settings_path)

try:
    # =============================
    # script is inteded to be launched minimized and will un minimize on frist print/error

    # WIPsetup_terminal_colors_and_unminimize_plus_foreground_on_first_print()

    # =============================

    stopped_count, stale_count, failed_messages = stop_processes_from_pid_file(pid_path)

    if failed_messages:
        raise RuntimeError("Failed to stop these PID(s):\n" + "\n".join(failed_messages))

    if stopped_count == 0:
        if stale_count == 0:
            print(f'[Info] No PID file found at "{pid_path}".')
            print("This could mean it was already stopped via this script.")
        else:
            print(f"[Info] Nothing to stop. Removed {stale_count} stale PID entries from {pid_path}.")
        input("Press enter to exit")
        close_terminal()
        sys.exit(0)

    print_success(f"[Success] Stopped {stopped_count} process(es).")
    if stale_count:
        print_success(f"[Info] Removed {stale_count} stale PID entries.")
    time.sleep(sleep_before_close_on_success_s)
    close_terminal()
    sys.exit(0)

except Exception as e:
    print_traceback(f"[Error] Failed to stop process: {e}")
    input("[Error (see abov)] Press enter to exit")

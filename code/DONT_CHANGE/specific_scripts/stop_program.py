# ==========================================================================
# package imports

import os
import sys
import time

# ==========================================================================
# add root dir for debug cases where this script is called on its own:
root_dir = os.path.dirname(__file__) + "\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# ==========================================================================
# import from common variables and developer settings
from DONT_CHANGE.specific_scripts.common_code import (
    close_terminal,
    make_abs_path_relative_to_file,
    print_traceback,
    stop_processes_from_pid_file,
)
from DONT_CHANGE.specific_scripts.common_variables import developer_settings_path, process_id_file_path

# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(process_id_file_path, developer_settings_path)

try:
    stopped_count, stale_count, failed_messages = stop_processes_from_pid_file(pid_path)

    if failed_messages:
        raise RuntimeError("Failed to stop these PID(s):\n" + "\n".join(failed_messages))

    if stopped_count == 0:
        if stale_count == 0:
            print(f"[Info] No PID file found at {pid_path}.")
            print("This could mean it was already stopped via this script.")
        else:
            print(f"[Info] Removed {stale_count} stale PID entries from {pid_path}. No more apparently open to close")
        input("Press enter to exit")
        close_terminal()
        sys.exit(0)

    print(f"[Success] Stopped {stopped_count} process(es).")
    if stale_count:
        print(f"[Info] Removed {stale_count} stale PID entries.")
    time.sleep(1)
    close_terminal()
    sys.exit(0)

except Exception as e:
    print_traceback(f"[Error] Failed to stop process: {e}", add_press_enter_to_exit=True)

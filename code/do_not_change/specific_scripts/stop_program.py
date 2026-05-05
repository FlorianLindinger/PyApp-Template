# ==========================================================================
# package imports

import sys
import time

# ==========================================================================
# import from common variables and developer settings
from do_not_change.specific_scripts.common_code import (
    make_abs_path_relative_to_file,
    print_traceback,
    stop_processes_from_pid_file,
)
from do_not_change.specific_scripts.common_variables import developer_settings_path, process_id_file_path

# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(process_id_file_path, developer_settings_path)

try:
    stop_result = stop_processes_from_pid_file(pid_path)

    failed_messages = list(stop_result["failed_messages"])
    if failed_messages:
        raise RuntimeError("Failed to stop these PID(s):\n" + "\n".join(failed_messages))

    stopped_count = int(stop_result["stopped_count"])
    stale_count = int(stop_result["stale_count"])
    if stopped_count == 0:
        if stale_count == 0:
            print(f"[Info] No PID file found at {pid_path}.")
            print("This could mean it was already stopped via this script.")
        else:
            print(f"[Info] Removed {stale_count} stale PID entries from {pid_path}.")
        input("Press enter to exit")
        sys.exit(0)

    print(f"[Success] Stopped {stopped_count} process(es).")
    if stale_count:
        print(f"[Info] Removed {stale_count} stale PID entries.")
    time.sleep(1)
    sys.exit(0)

except Exception as e:
    print_traceback(f"[Error] Failed to stop process: {e}", add_press_enter_to_exit=True)

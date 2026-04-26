# ==========================================================================
# package imports

import os
import signal
import sys
import time

# ==========================================================================
# import from common variables and developer settings
from do_not_change.specific_scripts.common_variables import (
    developer_settings_path,
    print_traceback,
    process_id_file_path,
)

# ==========================================================================
# needed functions


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(process_id_file_path, developer_settings_path)

if not os.path.exists(pid_path):
    print(f"[Info] No PID file found at {pid_path}.")
    sys.exit(0)

try:
    with open(pid_path, encoding="utf-8") as f:
        pid = int(f.read().strip())

    os.kill(pid, signal.SIGTERM)
    print("[Success] Process stopped.")
    time.sleep(1)
    sys.exit(0)
except Exception as e:
    print_traceback(f"[Error] Failed to stop process: {e}", add_press_enter_to_exit=True)

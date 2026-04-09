# ==========================================================================
# package imports

import os
import subprocess
import sys
import time
import traceback

# ==========================================================================
# import from common variables and developer settings
from do_not_change.specific_scripts.common_variables import developer_settings_dir, developer_settings_path

sys.path.insert(0, developer_settings_dir)
import developer_settings

# ==========================================================================
# needed functions


def error_print(message, max_wrapper_len=20, wrapper_symbol="=", red=False):
    msg_len = len(message)
    if msg_len > max_wrapper_len:
        msg_len = max_wrapper_len
    if red == True:
        print(f"\033[91m{wrapper_symbol * msg_len}")
    else:
        print(wrapper_symbol * msg_len)
    print(message)
    print(wrapper_symbol * msg_len)
    print(traceback.format_exc(), end="")
    if red == True:
        print(f"{wrapper_symbol * msg_len}\033[0m")
    else:
        print(wrapper_symbol * msg_len)


def make_abs_path_relative_to_file(path, file):
    """makes a path absolute if relative with respect to the file (as if the file defined it)"""
    if not os.path.isabs(path):
        return os.path.normpath(os.path.dirname(file) + "\\" + path)
    else:
        return path


# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(developer_settings.process_id_file_path, developer_settings_path)

if not os.path.exists(pid_path):
    print(f"[Info] No PID file found at {pid_path}.")
    sys.exit(0)

try:
    with open(pid_path, encoding="utf-8") as f:
        pid = int(f.read().strip())

    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, shell=False)  # noqa:S603
    print("[Success] Process stopped.")
    time.sleep(1)
    sys.exit(0)
except Exception as e:
    error_print(f"[Error] Failed to stop process: {e}")
    input("Press Enter to close this window...")
    sys.exit(1)

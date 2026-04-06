# ==========================================================================
# package imports

import os
import subprocess
import sys
import time

# ==========================================================================
# import from helper_functions

file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(file_path + "\\..\\..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from do_not_change.specific_scripts.helper_functions import (
    error_print,
    make_abs_path_relative_to_file,
    settings,
    settings_file_path,
)

# ==========================================================================
# code execution

pid_path = make_abs_path_relative_to_file(settings["process_id_file_path"], settings_file_path)

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

# ==========================================================================
# package imports

import os
import subprocess
import sys
import time

# ==========================================================================
# import from common_code_and_variables.py

file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.normpath(file_path + "\\..\\..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from do_not_change.specific_scripts.common_code_and_variables import (
    error_print,
    make_abs_path_relative_to_file,
)
from do_not_change.specific_scripts.common_variables import developer_settings, developer_settings_path

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

"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.scripts._common_variables import developer_tools_dir
from DONT_CHANGE.specific_scripts.common_code import (
    ensure_python_distro,
    input_success,
    print_traceback,
    save_current_packages,
)

try:
    ensure_python_distro()
    path = developer_tools_dir + "\\current_python_packages -withoutVersion.txt"
    save_current_packages(path, with_version=False)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to save current package list without versions: {e}", add_press_enter_to_exit=True)

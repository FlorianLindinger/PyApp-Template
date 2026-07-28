"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.DONT_CHANGE.scripts._common_code import (
    ensure_python_distro,
    input_success,
    print_traceback,
    save_current_packages,
)
from backend.DONT_CHANGE.scripts._common_variables import current_python_packages_file_path_withoutVersion

try:
    ensure_python_distro()
    save_current_packages(current_python_packages_file_path_withoutVersion, with_version=False)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to save current package list without versions: {e}", add_press_enter_to_exit=True)

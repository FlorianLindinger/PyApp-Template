"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    delete_packages,
    ensure_python_distro,
    input_success,
    mark_frontend_packages_installed,
    print_traceback,
)

try:
    ensure_python_distro()
    delete_packages()
    mark_frontend_packages_installed()
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to reset Python environment without packages: {e}", add_press_enter_to_exit=True)

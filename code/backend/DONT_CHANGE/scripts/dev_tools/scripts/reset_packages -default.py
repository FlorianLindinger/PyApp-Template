"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.DONT_CHANGE.scripts._common_code import (
    delete_frontend_packages,
    ensure_python_distro,
    input_success,
    install_packages_from_file,
    print_traceback,
)
from backend.DONT_CHANGE.scripts._common_variables import DEFAULT_PACKAGES_PATH

try:
    ensure_python_distro()
    delete_frontend_packages()
    install_packages_from_file(DEFAULT_PACKAGES_PATH)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to reset Python environment with default packages: {e}", add_press_enter_to_exit=True
    )

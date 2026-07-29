"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.DONT_CHANGE.scripts.common_code import (
    ensure_python_distro,
    input_success,
    install_packages_from_file,
    print_traceback,
)
try:
    ensure_python_distro()
    install_packages_from_file(os.path.join(os.getcwd(), "requirements.txt"))
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to install packages from local requirements.txt: {e}", add_press_enter_to_exit=True
    )

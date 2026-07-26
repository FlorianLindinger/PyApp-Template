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
    save_current_packages_as_default,
)

try:
    ensure_python_distro()
    save_current_packages_as_default(with_version=False)

    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to set current Python packages as default without package versions: {e}",
        add_press_enter_to_exit=True,
    )

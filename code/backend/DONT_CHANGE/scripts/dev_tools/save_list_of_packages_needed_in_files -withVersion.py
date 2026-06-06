"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    input_success,
    print_traceback,
    save_requirements_of_root_folder_withVersion,
)

try:
    success = save_requirements_of_root_folder_withVersion()
    if not success:
        raise RuntimeError("Failed to determine needed packages with versions.")
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to save package list needed in files with versions: {e}",
        add_press_enter_to_exit=True,
    )

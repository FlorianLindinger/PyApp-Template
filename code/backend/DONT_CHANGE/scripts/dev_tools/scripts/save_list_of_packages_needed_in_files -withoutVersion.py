"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.DONT_CHANGE.scripts._common_code import (
    input_success,
    print_traceback,
    save_requirements_of_root_folder_noVersion,
)

try:
    success, output_path = save_requirements_of_root_folder_noVersion()

    if success:
        print()
        input_success("[Success] Press enter to exit")
    else:
        raise RuntimeError("Failed to determine needed packages.")
except Exception as e:
    print_traceback(
        f"[Error] Failed to save package list needed in files without versions: {e}",
        add_press_enter_to_exit=True,
    )

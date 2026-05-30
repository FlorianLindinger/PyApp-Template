"""WIP"""

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    ensure_python_distro,
    input_success,
    install_packages_from_file,
    print_traceback,
    save_requirements_of_root_folder_noVersion,
)
from DONT_CHANGE.specific_scripts.common_variables import (
    determined_needed_packages_output_file_path_noVersion,
)

try:
    ensure_python_distro()
    success, output_path = save_requirements_of_root_folder_noVersion(determined_needed_packages_output_file_path_noVersion)
    if not success:
        raise RuntimeError("Failed to determine needed packages.")

    install_packages_from_file(output_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to install packages needed in Python files: {e}", add_press_enter_to_exit=True)

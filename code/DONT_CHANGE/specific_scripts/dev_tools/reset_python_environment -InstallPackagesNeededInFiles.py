import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    input_success,
    install_packages_from_file,
    print_traceback,
    recreate_venv,
)
from DONT_CHANGE.specific_scripts.common_variables import (
    determined_needed_packages_output_file_path,
    excluded_folders_for_package_search,
    python_scripts_dir,
)
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import (
    save_required_packages,
)

try:
    path = determined_needed_packages_output_file_path
    save_required_packages(
        path,
        with_versions=False,
        folder=python_scripts_dir,
        ignored_folders=excluded_folders_for_package_search,
    )
    recreate_venv()
    install_packages_from_file(path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to reset Python environment with packages needed in files: {e}",
        add_press_enter_to_exit=True,
    )

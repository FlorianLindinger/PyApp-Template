import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    ensure_python_distro_and_venv,
    input_success,
    install_packages_from_file,
    print_traceback,
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
    save_required_packages(
        determined_needed_packages_output_file_path,
        with_versions=False,
        folder=python_scripts_dir,
        ignored_folders=excluded_folders_for_package_search,
    )
    ensure_python_distro_and_venv()
    install_packages_from_file(determined_needed_packages_output_file_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to install packages needed in Python files: {e}", add_press_enter_to_exit=True)

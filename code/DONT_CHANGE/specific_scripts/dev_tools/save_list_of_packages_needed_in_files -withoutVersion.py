import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import (
    developer_tools_dir,
    excluded_folders_for_package_search,
    python_scripts_dir,
)
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import (
    save_required_packages,
)

try:
    path = developer_tools_dir + "\\packages_needed_in_files -withoutVersion.txt"
    save_required_packages(
        path,
        with_versions=False,
        folder=python_scripts_dir,
        ignored_folders=excluded_folders_for_package_search,
    )
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to save package list needed in files without versions: {e}",
        add_press_enter_to_exit=True,
    )

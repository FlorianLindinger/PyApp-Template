import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import (
    delete_packages,
    input_success,
    install_packages_from_file,
    print_traceback,
)
from DONT_CHANGE.specific_scripts.common_variables import default_packages_file_path

try:
    delete_packages()
    install_packages_from_file(default_packages_file_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to reset Python environment with default packages: {e}", add_press_enter_to_exit=True
    )

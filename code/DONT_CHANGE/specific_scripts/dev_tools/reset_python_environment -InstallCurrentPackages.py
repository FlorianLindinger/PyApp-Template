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
    recreate_venv,
    save_current_packages_withVersion
)
from DONT_CHANGE.specific_scripts.common_variables import (
    determined_current_packages_file_path_withVersion,
)

try:
    ensure_python_distro_and_venv()
    save_current_packages_withVersion()
    recreate_venv()
    install_packages_from_file(determined_current_packages_file_path_withVersion)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to reset Python environment with current packages: {e}", add_press_enter_to_exit=True
    )

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import default_packages_file_path
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import install_requirements, recreate_venv

try:
    recreate_venv()
    install_requirements(default_packages_file_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to reset Python environment with default packages: {e}", add_press_enter_to_exit=True)

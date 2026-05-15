import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback, save_current_packages
from DONT_CHANGE.specific_scripts.common_variables import developer_tools_dir

try:
    path = developer_tools_dir + "\\current_python_packages -withVersion.txt"
    save_current_packages(path, with_version=True)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to save current package list with versions: {e}", add_press_enter_to_exit=True)

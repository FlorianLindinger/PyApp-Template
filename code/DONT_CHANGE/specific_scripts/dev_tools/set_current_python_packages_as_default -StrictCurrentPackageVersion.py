import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback, write_default_packages
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import get_freeze_lines

try:
    write_default_packages(get_freeze_lines())
    print()
    input_success("[Success] Press enter to exit")

except Exception as e:
    print_traceback(
        f"[Error] Failed to set current Python packages as default with strict package versions: {e}",
        add_press_enter_to_exit=True,
    )

import os
import sys

# add root dir for imports:
root_dir = os.path.dirname(__file__) + "\\..\\..\\.."
sys.path.insert(0, root_dir)

from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import (
    get_freeze_lines,
    requirement_names_without_versions,
    write_default_packages,
)

try:
    write_default_packages(requirement_names_without_versions(get_freeze_lines()))
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to set current Python packages as default without package versions: {e}",
        add_press_enter_to_exit=True,
    )

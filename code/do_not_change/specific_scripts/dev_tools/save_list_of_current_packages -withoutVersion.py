from do_not_change.specific_scripts.common_variables import developer_tools_folder_path, input_success, print_traceback
from do_not_change.specific_scripts.dev_tools._common_code import (
    save_current_packages,
)

try:
    path = developer_tools_folder_path + "current_python_packages -withoutVersion.txt"
    save_current_packages(path, with_versions=False)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to save current package list without versions: {e}", add_press_enter_to_exit=True)

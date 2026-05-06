from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import developer_tools_folder_path
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import (
    ensure_venv,
    install_requirements,
)

try:
    path = developer_tools_folder_path + "requirements.txt"
    ensure_venv()
    install_requirements(path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to install packages from local requirements.txt: {e}", add_press_enter_to_exit=True)

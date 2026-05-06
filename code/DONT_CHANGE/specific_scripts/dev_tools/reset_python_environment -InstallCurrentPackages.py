from DONT_CHANGE.specific_scripts.common_code import input_success, print_traceback
from DONT_CHANGE.specific_scripts.common_variables import (
    determined_current_packages_file_path,
)
from DONT_CHANGE.specific_scripts.dev_tools.dev_tools_common_code import (
    ensure_venv,
    get_freeze_lines,
    install_requirements,
    recreate_venv,
    write_lines,
)

try:
    ensure_venv()
    write_lines(determined_current_packages_file_path, get_freeze_lines())
    recreate_venv()
    install_requirements(determined_current_packages_file_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to reset Python environment with current packages: {e}", add_press_enter_to_exit=True
    )

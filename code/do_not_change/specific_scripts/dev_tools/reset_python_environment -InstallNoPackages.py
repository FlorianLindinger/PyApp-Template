from do_not_change.specific_scripts.common_variables import input_success, print_traceback
from do_not_change.specific_scripts.dev_tools._common_code import recreate_venv

try:
    recreate_venv()
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to reset Python environment without packages: {e}", add_press_enter_to_exit=True)

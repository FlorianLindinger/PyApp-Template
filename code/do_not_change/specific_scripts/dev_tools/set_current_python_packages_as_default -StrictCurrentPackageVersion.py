from do_not_change.specific_scripts.common_variables import input_success, print_traceback
from do_not_change.specific_scripts.dev_tools._common_code import get_freeze_lines, write_default_packages

try:
    write_default_packages(get_freeze_lines())
    print()
    input_success("[Success] Press enter to exit")

except Exception as e:
    print_traceback(
        f"[Error] Failed to set current Python packages as default with strict package versions: {e}",
        add_press_enter_to_exit=True,
    )

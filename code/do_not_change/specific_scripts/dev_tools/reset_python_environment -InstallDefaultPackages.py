from do_not_change.specific_scripts.common_variables import default_packages_file_path, input_success, print_traceback
from do_not_change.specific_scripts.dev_tools._common_code import install_requirements, recreate_venv

try:
    recreate_venv()
    install_requirements(default_packages_file_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to reset Python environment with default packages: {e}", add_press_enter_to_exit=True)

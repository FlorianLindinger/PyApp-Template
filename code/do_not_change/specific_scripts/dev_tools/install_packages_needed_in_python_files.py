from do_not_change.specific_scripts.common_code import input_success, print_traceback
from do_not_change.specific_scripts.common_variables import (
    excluded_folders_for_package_search,
    needed_packages_output_file_path,
    python_scripts_folder_path,
)
from do_not_change.specific_scripts.dev_tools.dev_tools_common_code import (
    ensure_venv,
    install_requirements,
    save_required_packages,
)

try:
    save_required_packages(
        needed_packages_output_file_path,
        with_versions=False,
        folder=python_scripts_folder_path,
        ignored_folders=excluded_folders_for_package_search,
    )
    ensure_venv()
    install_requirements(needed_packages_output_file_path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(f"[Error] Failed to install packages needed in Python files: {e}", add_press_enter_to_exit=True)

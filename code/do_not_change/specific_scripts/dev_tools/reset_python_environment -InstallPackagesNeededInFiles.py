from do_not_change.specific_scripts.common_variables import (
    excluded_folders_for_package_search,
    input_success,
    needed_packages_output_file_path,
    print_traceback,
    python_scripts_folder_path,
)
from do_not_change.specific_scripts.dev_tools._common_code import (
    install_requirements,
    recreate_venv,
    save_required_packages,
)

try:
    path = needed_packages_output_file_path
    save_required_packages(
        path,
        with_versions=False,
        folder=python_scripts_folder_path,
        ignored_folders=excluded_folders_for_package_search,
    )
    recreate_venv()
    install_requirements(path)
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to reset Python environment with packages needed in files: {e}",
        add_press_enter_to_exit=True,
    )

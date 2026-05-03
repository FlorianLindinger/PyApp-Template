from do_not_change.specific_scripts.common_code import input_success, print_traceback
from do_not_change.specific_scripts.common_variables import (
    developer_tools_folder_path,
    excluded_folders_for_package_search,
    python_scripts_folder_path,
)
from do_not_change.specific_scripts.dev_tools.dev_tools_common_code import (
    save_required_packages,
)

try:
    path = developer_tools_folder_path + "packages_needed_in_files -withVersion.txt"
    save_required_packages(
        path,
        with_versions=True,
        folder=python_scripts_folder_path,
        ignored_folders=excluded_folders_for_package_search,
    )
    print()
    input_success("[Success] Press enter to exit")
except Exception as e:
    print_traceback(
        f"[Error] Failed to save package list needed in files with versions: {e}",
        add_press_enter_to_exit=True,
    )

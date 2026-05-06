import os


def make_abs(x: str) -> str:
    return os.path.normpath(_file_dir + x)


def get_dir(x: str) -> str:
    return os.path.dirname(x)


_file_dir: str = get_dir(os.path.normpath(__file__)) + "\\"

# ========================
# === define variables ===
# ========================

developer_settings_path = make_abs(
    "..\\..\\developer_settings.py"
)

portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs("..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = make_abs("..\\..\\py_env")

script_wrapper_path = make_abs("script_wrapper.py")
browser_terminal_path = make_abs("browser_terminal.py")

python_scripts_folder_path = make_abs("..\\..\\")
icon_path = make_abs("..\\..\\icons\\icon.ico")

compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")

process_id_file_path = make_abs("..\\..\\..\\currently_running.pid")

default_packages_file_path = make_abs("..\\..\\developer_tools\\!DEFAULT_PYHON_PACKAGES.txt")
excluded_folders_for_package_search = ["DONT_CHANGE", "py_env", "icons", "developer_tools", "__pycache__"]

variable_in_default_packages_path_that_triggers_search_if_true = (
    "# auto_find_required_packages_here_and_reset_venv_to_them"
)

developer_tools_folder_path = make_abs("..\\..\\developer_tools\\")

determined_current_packages_file_path = make_abs(developer_tools_folder_path + "determined_current_packages.txt")

needed_packages_output_file_path = make_abs(developer_tools_folder_path + "auto_found_required_packages.txt")

# =============================
# === process the variables ===
# =============================

developer_settings_dir = get_dir(developer_settings_path)

if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"
if developer_tools_folder_path != "" and developer_tools_folder_path[-1] != "\\":
    developer_tools_folder_path += "\\"

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, get_dir(venv_dir_path))

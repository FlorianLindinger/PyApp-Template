import os


def make_abs(x: str) -> str:
    return os.path.normpath(os.path.dirname(os.path.normpath(__file__)) + "\\" + x)


# ========================
# === define variables ===
# ========================

# folders
python_scripts_dir = make_abs("..\\..")
py_env_dir = make_abs("..\\..\\py_env")
developer_tools_dir = make_abs("..\\..\\developer_tools")
DONT_CHANGE_dir = make_abs("..")
backend_packages_dir = make_abs("..\\..\\python_packages")

# scripts
portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs("..\\general_scripts\\create_portable_venv.bat")
script_wrapper_path = make_abs("script_wrapper.py")
browser_terminal_path = make_abs("browser_terminal.py")
compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")

# files
developer_settings_path = make_abs("..\\..\\developer_settings.py")
icon_path = make_abs("..\\..\\icons\\icon.ico")
process_id_file_path = make_abs("..\\..\\..\\currently_running.pid")
default_packages_file_path = make_abs("..\\..\\developer_tools\\!DEFAULT_PYHON_PACKAGES.txt")
determined_current_packages_file_path = make_abs(developer_tools_dir + "\\determined_current_packages.txt")
needed_packages_output_file_path = make_abs(developer_tools_dir + "\\auto_found_required_packages.txt")

# variables
excluded_folders_for_package_search = ["DONT_CHANGE", "py_env", "icons", "developer_tools", "__pycache__"]
variable_in_default_packages_path_that_triggers_search_if_true = (
    "# auto_find_required_packages_here_and_reset_venv_to_them"
)

# =============================
# === process the variables ===
# =============================

developer_settings_dir = os.path.dirname(developer_settings_path)

python_dist_path = py_env_dir + "\\py_dist"
python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
venv_dir_path = py_env_dir + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"
relative_venv_to_python_dist = os.path.relpath(python_dist_path, venv_dir_path)
import os


def make_abs(x: str) -> str:
    return os.path.normpath(_file_dir + x)


def get_dir(x: str) -> str:
    return os.path.dirname(x)


_file_dir: str = get_dir(os.path.normpath(__file__)) + "\\"

# =======================
# define variables

developer_settings_path = make_abs(
    "..\\..\\developer_settings.py"
)  # kind of unsused since scripts expect developer_settings to be at root for import

portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
portable_venv_creator_path = make_abs("..\\general_scripts\\create_portable_venv.bat")

py_env_folder_path = make_abs("..\\..\\py_env")

backend_python_exe_path = make_abs("..\\P\\P.exe")

script_wrapper_path = make_abs("script_wrapper.py")

python_scripts_folder_path = make_abs("..\\..\\")
icon_path = make_abs("..\\..\\icons\\icon.ico")

compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")

process_id_file_path = make_abs("..\\..\\..\\currently_running_without_terminal_id.pid")

default_packages_path = make_abs("..\\..\\developer_tools\\!DEFAULT_PYHON_PACKAGES.txt")

excluded_folders_for_package_search = ["do_not_change", "py_env", "icons", "developer_tools", "__pycache__"]

# =======================
# process variables

developer_settings_dir = get_dir(developer_settings_path)

if python_scripts_folder_path != "" and python_scripts_folder_path[-1] != "\\":
    python_scripts_folder_path += "\\"

python_dist_path = py_env_folder_path + "\\py_dist"
venv_dir_path = py_env_folder_path + "\\virt_env"
venv_exe_path = venv_dir_path + "\\Portable_Scripts\\python.bat"

python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
relative_venv_to_python_dist = os.path.relpath(python_dist_path, get_dir(venv_dir_path))

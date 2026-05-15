import os


def make_abs(x: str) -> str:
    return os.path.normpath(os.path.dirname(os.path.normpath(__file__)) + "\\" + x)


# ========================
# === define variables ===
# ========================

# folders
# ------------------------
python_scripts_dir = make_abs("..\\..")
py_env_dir = make_abs("..\\..\\py_env")
developer_tools_dir = make_abs("..\\..\\developer_tools")
DONT_CHANGE_dir = make_abs("..")
backend_packages_dir = make_abs("..\\..\\python_packages")
shortcut_output_dir = make_abs("..\\..\\..")
python_dist_path = py_env_dir + "\\py_dist"
windows_dir = os.environ.get("WINDIR", default="C:\\Windows")
packages_dir = py_env_dir + "\\packages"

# scripts
# ------------------------
python_code_path = make_abs("..\\..\\main_code.py")
portable_python_installer_path = make_abs("..\\general_scripts\\create_portable_python.bat")
script_wrapper_path = make_abs("script_wrapper.py")
browser_terminal_path = make_abs("browser_terminal.py")
compiled_terminal_path = make_abs("..\\terminal_emulator\\compiled\\run.exe")
uncompiled_terminal_path = make_abs("..\\terminal_emulator\\terminal_emulator.py")
launcher_terminal = make_abs("..\\W.bat")
launcher_emulator = make_abs("..\\E.bat")
launcher_settings = make_abs("..\\S.bat")
launcher_browser = make_abs("..\\B.bat")
launcher_no_terminal = make_abs("..\\N.bat")
launcher_stop = make_abs("..\\Q.bat")

# files
# ------------------------
developer_settings_path = make_abs("..\\..\\developer_settings.py")
icon_path = make_abs("..\\..\\icons\\icon.ico")
settings_icon_path = make_abs("..\\..\\icons\\settings.ico")
stop_icon_path = make_abs("..\\..\\icons\\stop.ico")
process_id_file_path = make_abs("..\\..\\..\\currently_running.pid")
default_packages_file_path = make_abs("..\\..\\developer_tools\\!DEFAULT_PYHON_PACKAGES.txt")
determined_current_packages_file_path_withVersion = make_abs(
    developer_tools_dir + "\\determined_current_packages_withVersion.txt"
)
determined_current_packages_file_path_noVersion = make_abs(
    developer_tools_dir + "\\determined_current_packages_noVersion.txt"
)
determined_needed_packages_output_file_path_noVersion = make_abs(
    developer_tools_dir + "\\auto_found_required_packages_noVersion.txt"
)
determined_needed_packages_output_file_path_withVersion = make_abs(
    developer_tools_dir + "\\auto_found_required_packages_withVersion.txt"
)
python_version_indicator_file_path = developer_tools_dir + "\\current_python_version.txt"
play_sound_on_crash_default = windows_dir + "\\Media\\Windows Critical Stop.wav"
play_sound_on_failure_default = windows_dir + "\\Media\\Windows Critical Stop.wav"
play_sound_on_success_default = windows_dir + "\\Media\\notify.wav"

# variables
# ------------------------
excluded_folders_for_package_search = [
    "DONT_CHANGE",
    "py_env",
    "icons",
    "developer_tools",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tmp",
]
variable_in_default_packages_path_that_triggers_search_if_true = (
    "# auto_find_required_packages_here_and_reset_installed_packages_to_them"
)

# =============================
# === process the variables ===
# =============================

developer_settings_dir = os.path.dirname(developer_settings_path)
python_exe_path = os.path.normpath(python_dist_path + "\\python.exe")
script_for_set_python_and_pip_target = python_dist_path + "\\tools\\open_terminal_with_set_python_and_pip_target.bat"

import os


def make_abs(x: str) -> str:
    return os.path.normpath(os.path.dirname(os.path.normpath(__file__)) + "\\" + x)


# ========================
# === define variables ===
# ========================

# backend related
# ------------------------
# on change of all backend: stuff has to be changed manually (see finish_backend_installation.py) or regenerated automatically by deleting the previous folder:
backend_python_exe = make_abs("..\\P\\P.exe")  # has to match python_exe_name in install_backend_python.bat
backend_python_dir = os.path.dirname(backend_python_exe)
backend_python_pth_file = backend_python_dir + "\\python312._pth"
backend_python_zip_rel_path = "python312.zip"
backend_packages_dir = make_abs("..\\backend_py_pckgs")
backend_package_requirements_file = make_abs("..\\backend_packages_requirements.txt")

# frontend related
# ------------------------
frontend_env_dir = make_abs("..\\..\\py_env")
frontend_packages_dir = frontend_env_dir + "\\packages"
frontend_python_dir = frontend_env_dir + "\\py_dist"
frontend_script_for_set_python_and_pip_target = (
    frontend_python_dir + "\\tools\\open_terminal_with_set_python_and_pip_target.bat"
)
dev_tools_referal_note_file_name = (
    frontend_env_dir + "\\USE developer_tools FOLDER (IN PARENT FOLDER) TO CHANGE PACKAGES"
)

# folders
# ------------------------
windows_dir = os.environ.get("WINDIR", default="C:\\Windows")
python_scripts_dir = make_abs("..\\..")
developer_tools_dir = make_abs("..\\..\\developer_tools")
DONT_CHANGE_dir = make_abs("..")
shortcut_output_dir = make_abs("..\\..\\..")

# scripts
# ------------------------
python_code_path = make_abs("..\\..\\main_code.py")
script_wrapper_path = make_abs("script_wrapper.py")
browser_terminal_path = make_abs("..\\browser_terminal\\browser_terminal.py")
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
python_version_indicator_file_path = developer_tools_dir + "\\current_python_version.txt"
play_sound_on_crash_default = windows_dir + "\\Media\\Windows Critical Stop.wav"
play_sound_on_failure_default = windows_dir + "\\Media\\Windows Critical Stop.wav"
play_sound_on_success_default = windows_dir + "\\Media\\notify.wav"
determined_current_packages_file_path_withVersion = (
    developer_tools_dir + "\\determined_current_packages_withVersion.txt"
)
determined_current_packages_file_path_noVersion = developer_tools_dir + "\\determined_current_packages_noVersion.txt"
determined_needed_packages_output_file_path_noVersion = (
    developer_tools_dir + "\\auto_found_required_packages_noVersion.txt"
)
determined_needed_packages_output_file_path_withVersion = (
    developer_tools_dir + "\\auto_found_required_packages_withVersion.txt"
)
CORRECT_START_SIGNAL_FILE_PATH = make_abs("..\\signal_that_program_started_correctly.signal")

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
python_download_ftp_url = "https://www.python.org/ftp/python/"
python_download_excluded_base_msi_names = {"path", "appendpath", "pip", "launcher"}
python_download_timeout_s = 120


# =============================
# === derived/less-flexible variables ===
# =============================

developer_settings_dir = os.path.dirname(developer_settings_path)
frontend_python_exe = os.path.normpath(frontend_python_dir + "\\python.exe")
rel_path_from_backend_python_to_backend_packages = os.path.relpath(backend_packages_dir, backend_python_dir)

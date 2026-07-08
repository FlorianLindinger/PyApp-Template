"""WIP"""

import os


def make_abs(x: str) -> str:
    return os.path.normpath(os.path.dirname(os.path.normpath(__file__)) + "\\" + x)


# ========================
# === define variables ===
# ========================

# backend related
# ------------------------
# Change backend Python version in install_backend_python.bat.
backend_python_dir = make_abs("..\\backend_python")  # Update contents of backend_python_pth_file and pyproject.toml
backend_python_pth_file = (
    backend_python_dir + "\\python312._pth"
)  # must match Python version in install_backend_python.bat
backend_python_zip_rel_path = "python312.zip"  # must match Python version in install_backend_python.bat
backend_packages_dir = make_abs("..\\backend_packages")  # Update contents of backend_python_pth_file and pyproject.toml
backend_package_requirements_file = make_abs("..\\backend_packages_list.txt")
backend_files_to_delete_on_install = ["sqlite3.dll", "python.cat"]

# frontend related
# ------------------------
frontend_script_wrapper_path = make_abs("frontend\\script_wrapper.py")
frontend_packages_dir = make_abs("..\\..\\py_env\\packages")  # UPDATE GITIGNORE
frontend_python_dir = make_abs("..\\..\\py_env\\py_dist")  # UPDATE GITIGNORE
frontend_packages_are_installed_marker_filename = "_DELETE_THIS_TO_REINSTALL_ONLY_DEFAULT_PACKAGES_"
frontend_launcher_for_pip_install_terminal = (
    frontend_python_dir + "\\tools\\open_terminal_with_set_python_and_pip_target.bat"
)
dev_tools_referal_note_path = (
    os.path.dirname(frontend_packages_dir) + "\\_USE developer_tools FOLDER (IN PARENT FOLDER) TO CHANGE PACKAGES_"
)  # UPDATE GITIGNORE

# folders
# ------------------------
windows_dir = os.environ.get("WINDIR", default="C:\\Windows")
python_scripts_dir = make_abs("..\\..\\..")
developer_tools_dir = make_abs("..\\..\\developer_tools")  # UPDATE GITIGNORE
DONT_CHANGE_dir = make_abs("..")
shortcut_output_dir = make_abs("..\\..\\..\\..")  # UPDATE GITIGNORE
starter_batches_folder = make_abs("..\\B")
temporary_folder = DONT_CHANGE_dir = make_abs("..\\temporary")

# scripts
# ------------------------
start_program_script = make_abs("start_program.py")
python_script_path = make_abs("..\\..\\..\\main_script.py")
background_watchdog_path = make_abs("background_watchdog.py")
start_time_dummy_main_script = make_abs("..\\backend_test_tools\\helper_scripts\\start_time_dummy_main_script.py")
launcher_terminal = starter_batches_folder + "\\W.bat"
launcher_emulator = starter_batches_folder + "\\E.bat"
launcher_settings = starter_batches_folder + "\\S.bat"
launcher_browser = starter_batches_folder + "\\B.bat"
launcher_no_terminal = starter_batches_folder + "\\N.bat"
launcher_stop = starter_batches_folder + "\\Q.bat"
launcher_log = starter_batches_folder + "\\L.bat"
rich_traceback_printer_path=make_abs("_print_rich_traceback.py")

# files
# ------------------------

developer_settings_path = make_abs("..\\..\\developer_settings.py")
icon_path = make_abs("..\\..\\icons\\icon.ico")
settings_icon_path = make_abs("..\\..\\icons\\settings.ico")
stop_icon_path = make_abs("..\\..\\icons\\stop.ico")
log_icon_path = make_abs("..\\..\\icons\\log.ico")
success_icon_path = make_abs("..\\..\\icons\\success.ico")
failure_icon_path = make_abs("..\\..\\icons\\failure.ico")
crash_icon_path = make_abs("..\\..\\icons\\crash.ico")
process_id_file_path = make_abs("..\\..\\..\\_CURRENTLY_RUNNING_.pid")
default_packages_file_path = make_abs("..\\..\\developer_tools\\_DEFAULT_PYHON_PACKAGES_.txt")  # UPDATE GITIGNORE
python_version_indicator_file_path = developer_tools_dir + "\\_CURRENT_PYTHON_VERSION_.txt"
CORRECT_START_SIGNAL_FILE_PATH = temporary_folder + "\\signal_that_program_started_correctly.signal"
traceback_json_path = temporary_folder + "\\traceback_info.json"
play_sound_after_crash_default = windows_dir + "\\Media\\Windows Critical Stop.wav"
play_sound_after_failure_default = windows_dir + "\\Media\\Windows Critical Stop.wav"
play_sound_after_success_default = windows_dir + "\\Media\\notify.wav"
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
env_var_to_signal_startup_time_measurement = "PYAPP_TEMPLATE_ACTIVE_STARTUP_TIME_MEASUREMENT"
EMPTY_ARG_INDICATOR: str = "__EMPTY__"


# =============================
# === derived/less-flexible variables ===
# =============================

backend_python_exe = backend_python_dir + "\\python.exe"
developer_settings_dir = os.path.dirname(developer_settings_path)
frontend_python_exe = frontend_python_dir + "\\python.exe"
rel_path_from_backend_python_to_backend_packages = os.path.relpath(backend_packages_dir, backend_python_dir)
frontend_packages_are_installed_marker_path = (
    frontend_packages_dir + "\\" + frontend_packages_are_installed_marker_filename
)

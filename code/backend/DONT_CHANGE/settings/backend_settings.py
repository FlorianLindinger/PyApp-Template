"""WIP"""

# ======================================
# === helper imports and definitions ===
# ======================================

import os


def make_abs(x: str) -> str:
    """Make path absolute to this file if relative."""
    return os.path.normpath(x if os.path.isabs(x) else os.path.join(os.path.dirname(__file__), x))


def get_backend_settings(settings_path: str) -> tuple[str, str]:
    """Get the backend Python major/minor version and installation path."""
    settings_path = make_abs(settings_path)
    values: dict[str, str] = {}
    with open(settings_path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    backend_python_version = values["backend_python_version"]
    backend_python_major_minor_version = "".join(backend_python_version.split(".")[:2])
    backend_python_dir = os.path.normpath(
        os.path.join(os.path.dirname(settings_path), values["backend_python_install_dir_relative_path"])
    )
    return backend_python_major_minor_version, backend_python_dir


# ========================
# === define variables ===
# ========================

# folders
# ------------------------

DONT_CHANGE_DIR = make_abs("..")
BACKEND_DIR = make_abs("..\\..")
PYTHON_SCRIPTS_DIR = make_abs("..\\..\\..")
SHORTCUT_OUTPUT_DIR = make_abs("..\\..\\..\\..")  # UPDATE GITIGNORE
WINDOWS_DIR = os.environ.get("WINDIR", default="C:\\Windows")
ICON_DIR = BACKEND_DIR + "\\icons"
TEMPORARY_DIR = DONT_CHANGE_DIR + "\\temporary"
SHORTCUT_TARGET_DIR = DONT_CHANGE_DIR + "\\scripts\\shortcut_targets"
ENTRY_BATCHES_DIR = DONT_CHANGE_DIR + "\\B"
BACKEND_TOOLS_DIR = DONT_CHANGE_DIR + "\\backend_tools"


# backend related
# ------------------------

_backend_settings_ini_path = "backend_settings.ini"
_backend_python_major_minor_version, BACKEND_PYTHON_DIR = get_backend_settings(_backend_settings_ini_path)

BACKEND_PYTHON_pth_FILE = BACKEND_PYTHON_DIR + f"\\python{_backend_python_major_minor_version}._pth"
BACKEND_PYTHON_ZIP_REL_PATH = f"python{_backend_python_major_minor_version}.zip"
BACKEND_PACKAGES_DIR = (
    DONT_CHANGE_DIR + "\\backend_packages"
)  # UPDATE contents of BACKEND_PYTHON_pth_FILE + .gitignore + pyproject.toml
BACKEND_PACKAGE_REQUIREMENTS_FILE = make_abs("backend_packages_list.txt")
BACKEND_BUILD_TOOLS_REQUIREMENTS_FILE = make_abs("backend_build_tools_list.txt")
BACKEND_FILES_TO_DELETE_AFTER_INSTALL = ["sqlite3.dll", "python.cat"]

# frontend related
# ------------------------

FRONTEND_SCRIPT_WRAPPER_PATH = SHORTCUT_TARGET_DIR + "\\child_scripts\\frontend_python\\script_wrapper.py"
FRONTEND_PACKAGES_DIR = BACKEND_DIR + "\\packages"  # UPDATE contents of .gitignore + pyproject.toml
FRONTEND_PYTHON_DIR = BACKEND_DIR + "\\python"  # UPDATE  contents of.gitignore + pyproject.toml
FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH = (
    FRONTEND_PACKAGES_DIR + "\\_DELETE_THIS_TO_REINSTALL_ONLY_DEFAULT_PACKAGES_"
)
FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL = (
    FRONTEND_PYTHON_DIR + "\\tools\\open_terminal_with_set_python_and_pip_target.bat"
)
DEV_TOOLS_REFERAL_NOTE_PATH = (
    os.path.dirname(FRONTEND_PACKAGES_DIR) + "\\USE dev_tools FOLDER (IN PARENT FOLDER) TO CHANGE PACKAGES"
)  # UPDATE GITIGNORE
PYTHON_VERSION_INDICATOR_FILE_PATH = FRONTEND_PYTHON_DIR + "\\PYTHON_VERSION.txt"

# scripts
# ------------------------

START_PROGRAM_PATH = SHORTCUT_TARGET_DIR + "\\start_program.py"
MAIN_PY_SCRIPT_PATH = PYTHON_SCRIPTS_DIR + "\\main.py"
BACKGROUND_WATCHDOG_PATH = SHORTCUT_TARGET_DIR + "\\child_scripts\\backend_python\\background_watchdog.py"
START_TIME_DUMMY_MAIN_PY_PATH = BACKEND_TOOLS_DIR + "\\helper_scripts\\start_time_dummy_main_script.py"
PROCESS_EXIT_PATH = SHORTCUT_TARGET_DIR + "\\child_scripts\\backend_python\\process_exit.py"

# shorcut launchers related
# ------------------------

LAUNCHER_TERMINAL = ENTRY_BATCHES_DIR + "\\W.bat"
LAUNCHER_OPEN_SETTINGS = ENTRY_BATCHES_DIR + "\\S.bat"
LAUNCHER_NO_TERMINAL = ENTRY_BATCHES_DIR + "\\N.bat"
LAUNCHER_STOP = ENTRY_BATCHES_DIR + "\\Q.bat"
LAUNCHER_OPEN_LOG_DIR = ENTRY_BATCHES_DIR + "\\L.bat"
LAUNCHER_OPEN_CRASH_LOG_DIR = ENTRY_BATCHES_DIR + "\\C.bat"
LAUNCHER_OPEN_MAIN_PY = ENTRY_BATCHES_DIR + "\\M.bat"

# icon related ("" means no change)
# ------------------------

ICON_PATH = ICON_DIR + "\\icon.ico"
SETTINGS_ICON_PATH = ICON_DIR + "\\settings.ico"
STOP_ICON_PATH = ICON_DIR + "\\stop.ico"
LOG_ICON_PATH = ICON_DIR + "\\log.ico"
SUCCESS_ICON_PATH = ICON_DIR + "\\success.ico"
FAILURE_ICON_PATH = ICON_DIR + "\\failure.ico"
CRASH_ICON_PATH = ICON_DIR + "\\crash.ico"
CRASH_LOG_ICON_PATH = ICON_DIR + "\\crash_log.ico"
OPEN_MAIN_PY_ICON_PATH = ICON_DIR + "\\open_main_py.ico"
KEYBOARD_INTERRUPT_ICON_PATH = ICON_DIR + "\\keyboardInterrupt.ico"

ICON_PNG_DIR = ICON_DIR
ICON_FALLBACK_PNG_DIR = DONT_CHANGE_DIR + "\\icon_related"
ICON_DELETE_TIMEOUT_SECONDS = 2.0
ICON_DELETE_RETRY_DELAY_SECONDS = 0.05
_base = ("icon.png", "512x512:34babea5", "default_icon.png")
# fmt:off
ICON_GENERATION_SETTINGS = [
    # output ICO, base PNG, base PNG ID, fallback base PNG, overlay PNG, overlay PNG ID, fallback overlay PNG
    (ICON_PATH, *_base, None, None, None),
    (SETTINGS_ICON_PATH, *_base, "settings.png", "512x512:19c7e6d8", "default_settings.png"),
    (STOP_ICON_PATH, *_base, "stop.png", "512x512:0f35bd9e", "default_stop.png"),
    (LOG_ICON_PATH, *_base, "log.png", "512x512:66c0a178", "default_log.png"),
    (SUCCESS_ICON_PATH, *_base, "success.png", "512x512:c33e7909", "default_success.png"),
    (FAILURE_ICON_PATH, *_base, "failure.png", "512x512:93eddb87", "default_failure.png"),
    (CRASH_ICON_PATH, *_base, "crash.png", " 512x512:d2dd80f5", "default_crash.png"),
    (CRASH_LOG_ICON_PATH, *_base, "crash_log.png", "512x512:99dee2ae", "default_crash_log.png"),
    (OPEN_MAIN_PY_ICON_PATH, *_base, "open_main_py.png", "512x512:3bd1b4b4", "default_open_main_py.png"),
    (KEYBOARD_INTERRUPT_ICON_PATH,*_base,"keyboardInterrupt.png","512x512:0c4eac7f","default_keyboardInterrupt.png"),
]
# fmt:on

# PNG placeholders created by icon_related/generate_PNGs_to_be_replaced.py
PNG_GENERATION_OUTPUT_DIR = ICON_FALLBACK_PNG_DIR + "\\created_PNGS_to_be_replaced"
PNG_GENERATION_SIZE = 512
PNG_GENERATION_FONT_FAMILY = "Arial"
PNG_GENERATION_FONT_SIZE = 180
PNG_GENERATION_MIN_FONT_SIZE = 20
PNG_GENERATION_BOLD = True
PNG_GENERATION_PADDING = 12
PNG_GENERATION_TEXT_COLOR = (210, 0, 0, 255)
PNG_GENERATION_BACKGROUND_COLOR = (255, 255, 255, 255)
# fmt:off
PNG_GENERATION_ITEMS = {
    "icon.png": ["Replace to change", "base icon.", "Run", '"regenerate icons"', "afterwards"],
    "settings.png": ["Replace to change", "settings sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "stop.png": ["Replace to change", "stop sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "log.png": ["Replace to change", "log sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "success.png": ["Replace to change", "success sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "failure.png": ["Replace to change", "failure sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "crash.png": ["Replace to change", "crash sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "crash_log.png": ["Replace to change", "crash-log sub-icon.", "Run", '"regenerate icons"', "afterwards"],
    "open_main_py.png": ["Replace to change", "open-main.py", "sub-icon. Run", '"regenerate icons"', "afterwards"],
    "keyboardInterrupt.png": ["Replace to change","keyboard-interrupt","sub-icon. Run",'"regenerate icons"',"afterwards"],
}
# fmt:on

# untracked tmp files files
# ------------------------

CORRECT_START_SIGNAL_FILE_PATH = TEMPORARY_DIR + "\\signal_that_program_started_correctly.signal"
PROCESS_ID_FILE_PATH = PYTHON_SCRIPTS_DIR + "\\_CURRENTLY_RUNNING_.pid"
TMP_TRACEBACK_JSON_PATH = TEMPORARY_DIR + "\\last_crash_log.json"

# untracked developer-tools folder related
# ------------------------

DEV_TOOLS_FOR_PACKAGES_DIR = BACKEND_DIR + "\\dev_tools\\change python packages"  # UPDATE GITIGNORE
CURRENT_PACKAGES_WITH_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\determined_current_packages_withVersion.txt"
CURRENT_PACKAGES_NO_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\determined_current_packages_noVersion.txt"
NEEDED_PACKAGES_NO_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\auto_found_required_packages_noVersion.txt"
NEEDED_PACKAGES_WITH_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\auto_found_required_packages_withVersion.txt"

# remaining files
# ------------------------

DEV_SETTINGS_PATH = BACKEND_DIR + "\\developer_settings.py"
DEFAULT_PACKAGES_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\DEFAULT_PYTHON_PACKAGES.txt"  # UPDATE GITIGNORE
PIPREQS_MAPPING_PATH = BACKEND_PACKAGES_DIR + "\\pipreqs\\mapping"
DEFAULT_SOUND_AFTER_CRASH = WINDOWS_DIR + "\\Media\\Windows Critical Stop.wav"
DEFAULT_SOUND_AFTER_FAILURE = WINDOWS_DIR + "\\Media\\Windows Critical Stop.wav"
DEFAULT_SOUND_AFTER_SUCCESS = WINDOWS_DIR + "\\Media\\notify.wav"
DEFAULT_SOUND_AFTER_KeyboardInterrupt = ""

# variables
# ------------------------

EXCLUDED_FOLDERS_FOR_PACKAGE_SEARCH = [
    "backend",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tmp",
]
VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE = (
    "# auto_find_required_packages_here_and_reset_installed_packages_to_them"
)
ENV_VAR_TO_SIGNAL_STARTUP_TIME_MEASUREMENT = "PYAPP_TEMPLATE_ACTIVE_STARTUP_TIME_MEASUREMENT"
EMPTY_ARG_INDICATOR = "__EMPTY__"
FAILURE_TERMINAL_COLORS = "4F"
CRASH_TERMINAL_COLORS = "4F"
KEYBOARDINTERRUPT_TERMINAL_COLORS = ""
SUCCESS_TERMINAL_COLORS = "2F"
ERROR_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
RICH_TRACEBACK_COLOR_THEME = {
    "code": "monokai",
    "background": "#272822",
    "border": "bright_red",
    "syntax_border": "bold bright_red",
    "label": "bold bright_white",
    "metadata": "bright_black",
    "text": "bright_white",
    "syntax_pointer": "bold bright_yellow",
}

# =======================================
# === derived/less-flexible variables ===
# =======================================

BACKEND_PYTHON_EXE = BACKEND_PYTHON_DIR + "\\python.exe"
DEV_SETTINGS_DIR = os.path.dirname(DEV_SETTINGS_PATH)
FRONTEND_PYTHON_EXE = FRONTEND_PYTHON_DIR + "\\python.exe"
REL_PATH_FROM_BACKEND_PYTHON_TO_ITS_PACKAGES = os.path.relpath(BACKEND_PACKAGES_DIR, BACKEND_PYTHON_DIR)

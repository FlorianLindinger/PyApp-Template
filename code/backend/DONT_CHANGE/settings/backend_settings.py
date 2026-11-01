"""Define internal launcher paths, bootstrap settings and generated-asset configuration."""

# ======================================
# === helper imports and definitions ===
# ======================================

import os


def make_abs(x: str) -> str:
    """Make path absolute to this file if relative."""
    return os.path.normpath(
        x if os.path.isabs(x) else os.path.join(os.path.dirname(__file__), x)
    )


def get_ini_file_settings(settings_path: str) -> tuple[str, str]:
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
        os.path.join(
            os.path.dirname(settings_path),
            values["backend_python_install_dir_relative_path"],
        )
    )
    return backend_python_major_minor_version, backend_python_dir

# The installer prepares and checks a replacement backend in a temporary folder
# before replacing the working installation. Its Python helper scripts import this
# settings file too, so they must see the temporary paths during that preparation.
def _staged_path(variable: str, default: str) -> str:
    """Use an installer-supplied temporary path, or the normal installed path.

    ensure_backend_python.ps1 sets PYAPP_BACKEND_STAGING and
    PYAPP_PACKAGES_STAGING for its installation/health-check subprocesses.
    For example, BACKEND_PACKAGES_DIR then points to
    temporary/backend-install-<unique-id>/backend_packages instead of the live
    DONT_CHANGE/backend_packages folder. Without this override, the preparation
    scripts could modify or check the live backend instead of its replacement.

    With no override, normal launches simply use ``default``. An override must
    resolve to a child of TEMPORARY_DIR; the temporary root itself is rejected.
    Resolving links and checking whole path components prevents an accidental
    override outside that tree. This function only selects/checks a path: the
    PowerShell installer creates folders, validates the new installation, swaps
    it into place, and handles rollback.
    """
    value = os.environ.get(variable)
    if not value:
        return default
    # Normalize the override and resolve filesystem links before comparing paths.
    value = os.path.realpath(value)
    base = os.path.realpath(TEMPORARY_DIR)
    # commonpath compares directories, unlike a string prefix test that would
    # also accept a sibling such as "temporary-other". Require a strict child.
    if os.path.commonpath([value, base]) != base or value == base:
        raise ValueError("Backend staging must be inside its temporary directory")
    return value

# ========================
# === define variables ===
# ========================
# fmt:off

# Optional installer version used when provisioning uv locally.
UV_VERSION = "0.8.22"

# ------------------------
# folders

# Layout changes also require reviewing batch/PowerShell bootstrap paths.
# Source scripts and icon assets are tracked; do not add them to .gitignore.
DONT_CHANGE_DIR = make_abs("..")
BACKEND_DIR = make_abs("..\\..")  # UPDATE root .gitignore's /code/backend/... rules if moved.
PYTHON_SCRIPTS_DIR = make_abs("..\\..\\..")  # UPDATE root .gitignore's /code/*.pid* rules if moved.
SHORTCUT_OUTPUT_DIR = make_abs("..\\..\\..\\..")  # UPDATE root .gitignore's /*.lnk rule if moved.
TEMPORARY_DIR = DONT_CHANGE_DIR + "\\temporary"  # UPDATE DONT_CHANGE/.gitignore and bootstrap's temporary path if moved.
APP_ACTIONS_DIR = DONT_CHANGE_DIR + "\\scripts\\actions"
# Keep shortcut targets short to leave room for a long project path.
ENTRY_BATCHES_DIR = DONT_CHANGE_DIR + "\\B"
WINDOWS_DIR = os.environ.get("WINDIR", default="C:\\Windows")

# ------------------------
# scripts

START_PROGRAM_PATH = APP_ACTIONS_DIR + "\\start_program.py"
MAIN_PY_SCRIPT_PATH = PYTHON_SCRIPTS_DIR + "\\main.py"
BACKGROUND_WATCHDOG_PATH = DONT_CHANGE_DIR + "\\scripts\\runtime\\background_watchdog.py"
PROCESS_EXIT_PATH = DONT_CHANGE_DIR + "\\scripts\\runtime\\process_exit.py"

# ------------------------
# shortcut launchers related

LAUNCHER_TERMINAL = ENTRY_BATCHES_DIR + "\\W.bat"
LAUNCHER_OPEN_SETTINGS = ENTRY_BATCHES_DIR + "\\S.bat"
LAUNCHER_NO_TERMINAL = ENTRY_BATCHES_DIR + "\\N.bat"
LAUNCHER_STOP = ENTRY_BATCHES_DIR + "\\Q.bat"
LAUNCHER_OPEN_LOG_DIR = ENTRY_BATCHES_DIR + "\\L.bat"
LAUNCHER_OPEN_CRASH_LOG_DIR = ENTRY_BATCHES_DIR + "\\C.bat"
LAUNCHER_OPEN_MAIN_PY = ENTRY_BATCHES_DIR + "\\M.bat"

# ------------------------
# tracked icon assets and generation inputs

ICON_DIR = BACKEND_DIR + "\\icons"
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
# IDs identify the shipped placeholder PNGs, not a developer's replacement art.
# Update an ID only when changing the corresponding shipped placeholder image.
ICON_GENERATION_SETTINGS = [
    # output ICO, base PNG, base PNG ID, fallback base PNG, overlay PNG, overlay PNG ID, fallback overlay PNG
    (ICON_PATH, *_base, None, None, None),
    (SETTINGS_ICON_PATH, *_base, "settings.png", "512x512:19c7e6d8", "default_settings.png"),
    (STOP_ICON_PATH, *_base, "stop.png", "512x512:0f35bd9e", "default_stop.png"),
    (LOG_ICON_PATH, *_base, "log.png", "512x512:66c0a178", "default_log.png"),
    (SUCCESS_ICON_PATH, *_base, "success.png", "512x512:c33e7909", "default_success.png"),
    (FAILURE_ICON_PATH, *_base, "failure.png", "512x512:93eddb87", "default_failure.png"),
    (CRASH_ICON_PATH, *_base, "crash.png", "512x512:d2dd80f5", "default_crash.png"),
    (CRASH_LOG_ICON_PATH, *_base, "crash_log.png", "512x512:99dee2ae", "default_crash_log.png"),
    (OPEN_MAIN_PY_ICON_PATH, *_base, "open_main_py.png", "512x512:3bd1b4b4", "default_open_main_py.png"),
    (KEYBOARD_INTERRUPT_ICON_PATH,*_base,"keyboardInterrupt.png","512x512:0c4eac7f","default_keyboardInterrupt.png"),
]

# ------------------------
# generated process state and legacy traceback fallback

# UPDATE root .gitignore's *.pid, *.pid.d/ and *.pid.lock rules if parent/suffix changes.
PROCESS_ID_FILE_PATH = PYTHON_SCRIPTS_DIR + "\\_CURRENTLY_RUNNING_.pid"
# Covered by TEMPORARY_DIR's ignore rule. Normal runs use runs/<id>/traceback.json.
TMP_TRACEBACK_JSON_PATH = TEMPORARY_DIR + "\\last_crash_log.json"

# ------------------------
# tracked package tools/defaults and ignored generated reports

DEV_TOOLS_FOR_PACKAGES_DIR = BACKEND_DIR + "\\dev_tools"  # UPDATE root .gitignore's report rule and tracked-input exceptions if moved.
# These four outputs use the folder's *.txt ignore rule; UPDATE .gitignore if
# moving one outside this folder or changing its suffix. Keep source inputs tracked.
CURRENT_PACKAGES_WITH_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\determined_current_packages_withVersion.txt"
CURRENT_PACKAGES_NO_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\determined_current_packages_noVersion.txt"
NEEDED_PACKAGES_NO_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\auto_found_required_packages_noVersion.txt"
NEEDED_PACKAGES_WITH_VERSION_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\auto_found_required_packages_withVersion.txt"

# ------------------------
# backend related

# Backend folder locations must also agree with the fixed PowerShell bootstrap
# paths. UPDATE DONT_CHANGE/.gitignore (including .previous backups)
# when changing installed runtime/package locations.
_backend_settings_ini_path = "backend_settings.ini"
_backend_python_major_minor_version, BACKEND_PYTHON_DIR = get_ini_file_settings(_backend_settings_ini_path)

BACKEND_PYTHON_DIR = _staged_path("PYAPP_BACKEND_STAGING", BACKEND_PYTHON_DIR)
BACKEND_PYTHON_pth_FILE = BACKEND_PYTHON_DIR + f"\\python{_backend_python_major_minor_version}._pth"
BACKEND_PYTHON_ZIP_REL_PATH = f"python{_backend_python_major_minor_version}.zip"
BACKEND_PACKAGES_DIR = _staged_path("PYAPP_PACKAGES_STAGING", DONT_CHANGE_DIR + "\\backend_packages")  # UPDATE DONT_CHANGE/.gitignore and relative ._pth package paths if moved.
# Requirement lists below are tracked installer inputs, not generated packages.
BACKEND_PACKAGE_REQUIREMENTS_FILE = make_abs("backend_packages.txt")
BACKEND_BUILD_TOOLS_REQUIREMENTS_FILE = make_abs("backend_build_tools.txt")
BACKEND_FILES_TO_DELETE_AFTER_INSTALL = ["sqlite3.dll", "python.cat"]

# ------------------------
# frontend related

FRONTEND_SCRIPT_WRAPPER_PATH = DONT_CHANGE_DIR + "\\scripts\\runtime\\script_wrapper.py"
# All markers, manifests, version files and helper batches inside these trees
# inherit their folder's ignore rule; they do not need individual ignore entries.
# UPDATE root .gitignore for both the live folder and sibling
# .staging-*, .previous and .failed directories if either location changes.
FRONTEND_PACKAGES_DIR = BACKEND_DIR + "\\packages"
FRONTEND_PYTHON_DIR = BACKEND_DIR + "\\python"
FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH = FRONTEND_PACKAGES_DIR + "\\_DELETE THIS TO REINSTALL ONLY DEFAULT PACKAGES"
FRONTEND_LAUNCHER_FOR_PIP_INSTALL_TERMINAL = FRONTEND_PYTHON_DIR + "\\tools\\open_terminal_with_set_python_and_pip_target.bat"
# Diagnostic text written on installation; health checks query the executable.
PYTHON_VERSION_INDICATOR_FILE_PATH = FRONTEND_PYTHON_DIR + "\\PYTHON_VERSION.txt"
# UPDATE root .gitignore's tracked-file exception and adjacent .lock.json rule
# if this filename changes. The runtime lock uses BACKEND_DIR/frontend-python.lock.json.
DEFAULT_PACKAGES_PATH = DEV_TOOLS_FOR_PACKAGES_DIR + "\\DEFAULT_PYTHON_PACKAGES.txt"

# ------------------------
# remaining files

DEV_SETTINGS_PATH = BACKEND_DIR + "\\developer_settings.py"
PIPREQS_MAPPING_PATH = BACKEND_PACKAGES_DIR + "\\pipreqs\\mapping"
DEFAULT_SOUND_AFTER_CRASH = WINDOWS_DIR + "\\Media\\Windows Critical Stop.wav"
DEFAULT_SOUND_AFTER_FAILURE = WINDOWS_DIR + "\\Media\\Windows Critical Stop.wav"
DEFAULT_SOUND_AFTER_SUCCESS = WINDOWS_DIR + "\\Media\\notify.wav"
# Ctrl+C has no default sound; an explicit WAV can still be configured per app.
DEFAULT_SOUND_AFTER_KeyboardInterrupt = ""

# variables
# ------------------------

# Explorer visibility only; this does not control .gitignore or Git tracking.
FOLDERS_TO_MAKE_HIDDEN_IN_SHORTCUT_AND_ROOT_FOLDERS = [
    ".git",
    ".agents",
    ".lprof",
    ".githooks",
    ".vscode",
    ".gitignore",
    ".gitattributes",
    ".ruff_cache",
    "__pycache__",
]
# Import-inference scan exclusions, independent of Git ignore rules.
EXCLUDED_FOLDERS_FOR_PACKAGE_SEARCH = [
    os.path.basename(BACKEND_DIR),
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    ".tmp",
]
VARIABLE_IN_DEFAULT_PACKAGES_THAT_TRIGGERS_SEARCH_IF_TRUE = (
    "# auto_find_required_packages_here_and_reset_installed_packages_to_them"
)
EMPTY_ARG_INDICATOR = "__EMPTY__"

# =======================================
# === derived/less-flexible variables ===
# =======================================

BACKEND_PYTHON_EXE = BACKEND_PYTHON_DIR + "\\python.exe"
DEV_SETTINGS_DIR = os.path.dirname(DEV_SETTINGS_PATH)
FRONTEND_PYTHON_EXE = FRONTEND_PYTHON_DIR + "\\python.exe"
REL_PATH_FROM_BACKEND_PYTHON_TO_ITS_PACKAGES = os.path.relpath(BACKEND_PACKAGES_DIR, BACKEND_PYTHON_DIR)

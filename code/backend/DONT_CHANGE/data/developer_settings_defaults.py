"""Default values of every setting in code/backend/developer_settings.py (do not edit).

A copy of the developer_settings.py this launcher version ships with. When a project's
developer_settings.py lacks a setting (e.g. one added by a newer launcher version), the launcher
uses the value from here and says so; expressions such as f"{program_name}" use the project's
own values. Never imported as a module; scripts/config.py reads the assignments with ast.

Settings marked [bootstrap] are also read by the Windows bootstrap before any Python
exists. Keep each of them on ONE line as a plain literal ("text", True, False, None):
no expressions, f-strings or line continuations.
"""

# Keeps the "str | None" annotations below working on Python 3.8 and 3.9.
from __future__ import annotations

# IMPORTANT  what almost every project sets: name, Python, packages, logging on/off, running twice.
# MEDIUM     behavior you sometimes want different: program end, window, start and stop, log files.
# LOW        special cases and cosmetics: shortcut names, uv, certificates, error report details.

# ==================================================================
# ==== IMPORTANT ===================================================
# ==================================================================

# --- Program ---
# Used for the shortcuts and window titles:
program_name = "PyApp-Template"

# --- Python and packages ---
# [bootstrap] Python version requested from uv:
#   ""        newest stable Python, chosen once and then kept (see dev tool update_python)
#   "3.14"    any 3.14.x (uv picks the newest patch)
#   "3.14.6"  exactly that patch
#   "3.14t"   free-threaded build; any other uv request string such as "pypy@3.11" also works
# Supported: every version uv can provide (Windows x64 currently 3.8.2 and newer).
# The launcher itself needs Python 3.8 or newer. Changing this later offers a migration menu.
python_version = "3.14"

# Packages the app needs: PyPI names with optional version limits, e.g. ["requests", "numpy>=2", "pillow==11.*"].
# Or paste a requirements.txt as a block: packages = """, then one package per line (# comments are fine), then """.
# The launcher installs exactly these, with the versions recorded in backend/generated/uv.lock (commit that file).
# A package removed here stays installed until you run the dev tool sync_packages.
# The dev tools add_packages, remove_packages and find_imports edit this list for you.
packages: list[str] | str = []

# --- Logging and prints ---
# Write a log file (location: log_path below). Logging turns stdout/stderr into pipes,
# so turn the terminal one off if the app needs a real console (TTY):
enable_log_for_terminal_start = True
# Without a terminal, the log is the only place where prints end up:
enable_log_for_no_terminal_start = True

# Text added before each print and input in the window. Accepts strftime codes, e.g. "%H:%M:%S | ". None: no text.
print_prepend: str | None = "%H:%M:%S | "
input_prepend: str | None = "%H:%M:%S > "

# --- Started while already running ---
#   "allow"    start another instance
#   "focus"    bring the running instance's window to the front instead (asks to replace it if it has no window)
#   "prevent"  show a message and do not start
#   "replace"  stop the running instance(s), then start
#   "ask"      ask whether to replace the running instance(s)
instance_policy = "allow"

# ==================================================================
# ==== MEDIUM ======================================================
# ==================================================================

# --- When the program ends ---
# success            end of file, sys.exit(0) or sys.exit()
# failure            anything that went wrong: an unhandled exception (including SyntaxError and missing packages),
#                    sys.exit(non-zero), a Python interpreter crash (where even try/except fails, e.g. an access
#                    violation or os.abort()), the program ending unexpectedly without a report, or a launcher error
# keyboard_interrupt the user pressed Ctrl+C

# Close the window right away (False: it stays open until Enter is pressed):
close_after_success = True
close_after_failure = False
close_after_keyboard_interrupt = False

# Open the normal log file:
open_log_file_after_success = False
open_log_file_after_failure = False
open_log_file_after_keyboard_interrupt = False

# Open the crash log (Ctrl+C does not count):
open_crash_log_after_failure = False

# Play the default Windows sound:
play_sound_after_success = False
play_sound_after_failure = True

# --- Window ---
# True:  classic console (conhost.exe). No tabs, looks more like an app, but text rendering and zoom are worse.
# False: Windows Terminal (wt.exe). Tabs, better text rendering and zoom.
#        Falls back to the classic console with a warning if Windows Terminal is not installed.
use_classic_terminal = True

# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,7=White,8=Gray,9=LightBlue:
terminal_bg_color: str | None = "9"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_text_color: str | None = "F"

# --- Starting and stopping ---
# Arguments passed to main.py:
args_for_main_py: list[str] = []

# Environment variables set for main.py, e.g. {"MY_SETTING": "1"}.
# PYTHON* variables have no effect on main.py itself, because it runs with -E.
environment_for_main_py: dict[str, str] = {}

# Working folder of the program. False: the folder of main.py. True: the folder of the starting shortcut.
start_in_shortcut_folder = False

# Stop shortcut and instance_policy "replace": seconds a running instance gets to close by itself
# (its windows receive a normal close request, a console app gets Ctrl+C) before it is terminated.
# 0 terminates immediately.
stop_timeout_seconds: float = 3

# --- Python location ---
# [bootstrap] Where the app's Python comes from:
#   "local"    uv installs it inside this project (code/backend/generated/pythons). Portable.
#   "uv_user"  uv installs it in its per-user folder, shared by projects.
python_source = "uv_user"

# --- Settings file and shortcut locations ---
# File that the Settings shortcut opens, for the people using the app (any file type; None: no such shortcut).
# Run Setup again after changing it:
user_settings_path: str | None = "..\\settings.py"

# The project folder always gets all enabled shortcuts. Setup removes earlier ones that are no longer wanted.
# Start Menu: a folder named after program_name with all enabled shortcuts:
start_menu_shortcuts = True
# Desktop: a list of "terminal", "no_terminal", "stop", "settings", "logs", "crash_logs", "main_py". Example: ["no_terminal"]
desktop_shortcuts: list[str] = []

# --- Log files ---
# Accepts strftime codes, e.g. "log_%Y-%m-%d_%H-%M-%S.txt". None: no log file.
# After changing the folder, run Setup again (the Logs shortcut opens it) and update the root .gitignore's /logs/* rule.
log_path: str | None = "..\\..\\logs\\log_%Y-%m-%d_%H-%M-%S.txt"
# A relative log_path starts at: False = this file, True = the folder of the starting shortcut.
log_path_is_relative_to_start_folder_if_relative = False

# Text added before each print and input in the log file (same format as print_prepend):
log_print_prepend: str | None = "%H:%M:%S | "
log_input_prepend: str | None = "%H:%M:%S > "

# --- Crash logs ---
# A text file with the error report, written after every failure and after Ctrl+C. Your prints are in the normal log.
enable_crash_log = True
# Accepts strftime codes, e.g. "crash_log_%Y-%m-%d_%H-%M-%S.txt". None: no crash log.
# After changing the folder, run Setup again (the Crash Logs shortcut opens it) and update the root .gitignore's /crash logs/* rule.
crash_log_path: str | None = "..\\..\\crash logs\\crash_log_%Y-%m-%d_%H-%M-%S.txt"
# A relative crash_log_path starts at: False = this file, True = the folder of the starting shortcut.
crash_log_path_is_relative_to_start_folder_if_relative = False

# ==================================================================
# ==== LOW =========================================================
# ==================================================================

# --- Shortcut names ---
# None: that shortcut is not created. The first one starts the app with a terminal (see use_classic_terminal).
terminal_shortcut_name: str | None = f"{program_name}"
no_terminal_shortcut_name: str | None = f"{program_name} (no Terminal)"
open_settings_shortcut_name: str | None = f"{program_name} - Settings"
stop_running_shortcut_name: str | None = f"Stop {program_name}"
open_log_folder_shortcut_name: str | None = f"{program_name} - Logs"
open_crash_log_folder_shortcut_name: str | None = f"{program_name} - Crash Logs"
open_main_py_shortcut_name: str | None = f"{program_name} - Edit Code"

# --- Startup ---
# Start with the window minimized:
start_minimized = False

# --- uv ---
# [bootstrap] Which uv is used and how it gets installed:
#   uv_prefer: which uv to use when both a global (on PATH) and a local (code/backend/generated/uv) uv exist: "global" | "local"
#   uv_install_if_missing: "global" (Astral's installer, adds uv to your user PATH) | "local" | "never"
#   uv_version: "" for the latest, an exact version like "0.11.32", or a range like ">=0.9,<1"
#   A global uv that does not satisfy uv_version is not changed; a local uv is installed instead.
#   If that uv cannot provide python_version, the newest uv is downloaded to %LOCALAPPDATA%\PyApp-Template\uv and used
#   from then on. It is not put on PATH, so your global uv stays the default. uv_install_if_missing = "never" or an exact
#   uv_version turns this off.
uv_prefer = "global"
uv_install_if_missing = "global"
uv_version = ""

# [bootstrap] For python_source = "uv_user": also register the Python in Windows (py launcher) and put python3.x.exe on PATH:
uv_user_python_visible_globally = True

# [bootstrap] uv download cache: "global" (uv's per-user cache) or "local" (code/backend/generated/uv-cache, grows over time):
uv_cache = "global"

# [bootstrap] Use Windows' certificate store for downloads (needed behind some company proxies):
use_system_certificates = False

# --- Error reports ---
# Date format in crash reports:
error_date_format = "%Y-%m-%d %H:%M:%S"

# Source lines of your own code shown before and after each failing line (0: none).
# Library code always shows just the failing line, like Python does.
traceback_lines_before: int = 3
traceback_lines_after: int = 3

# --- Windows Terminal only (use_classic_terminal = False) ---
# Tab bar color, e.g. "#3B78FF". None: the Windows Terminal profile's default.
tab_bar_color: str | None = "#3B78FF"


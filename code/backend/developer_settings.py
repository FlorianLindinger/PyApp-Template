"""Configure application identity, Python/uv, logging and launcher completion behavior.

Relative paths in this file are interpreted as relative to this file.

Settings marked [bootstrap] are also read by the Windows bootstrap before any Python
exists. Keep each of them on ONE line as a plain literal ("text", True, False, None):
no expressions, f-strings or line continuations.
"""

# Keeps the "str | None" annotations below working on Python 3.8 and 3.9.
from __future__ import annotations

# ===========================
# ==== Settings Overview ====
# ===========================

# 1. Important Settings: program name, Python version, shortcuts, startup and instances.
# 2. Python and Package Settings: the packages the app needs and where uv, Python and the packages come from.
# 3. Logging Settings: normal and crash-log locations, behavior and retention.
# 4. Program Finish/Crash Settings: what happens after success, failure, crashes, and Ctrl+C (keyboard_interrupt).
# 5. Traceback Settings: crash-report date format, context lines and colors.
# 6. Icon Settings: individual overlay size and alignment for generated shortcut icons.
# 7. Less Important Settings: application arguments.
# 8. Launcher Mode Specific Settings: classic-console and Windows Terminal appearance.

# ============================
# ==== Important Settings ====
# ============================

# ---------------------------------------
# Name of this program:
program_name = "PyApp-Template"
# ---------------------------------------
# program_name as ASCII art at the top of windows that stay open for a while (Setup, dev tools,
# installing Python or packages). Fonts: "future", "future_smooth" (both capitals only, drawn
# with box characters), "standard", "coder_mini". None: no banner.
app_name_banner_font: str | None = "future"
# ---------------------------------------
# [bootstrap] Python version requested from uv:
#   ""        newest stable Python, chosen once and then kept (see dev tool update_python)
#   "3.14"    any 3.14.x (uv picks the newest patch)
#   "3.14.6"  exactly that patch
#   "3.14t"   free-threaded build; any other uv request string such as "pypy@3.11" also works
# Supported: every version uv can provide (Windows x64 currently 3.8.2 and newer).
# The launcher itself needs Python 3.8 or newer. Changing this later offers a migration menu.
python_version = "3.14"
# ---------------------------------------
# Path to end-user settings file (None to disable). File type can be anything openable by vscode/editor.
# Run Setup again after changing it (the Settings shortcut opens it):
user_settings_path: str | None = "..\\settings.py"
# ---------------------------------------
# Names of created shortcuts (None to disable). Accepts for example f"{program_name}":
# The first one starts the app with a terminal (classic console or Windows Terminal, see section 8).
terminal_shortcut_name: str | None = f"{program_name}"
no_terminal_shortcut_name: str | None = f"{program_name} (no Terminal)"
open_settings_shortcut_name: str | None = f"{program_name} - Settings"
stop_running_shortcut_name: str | None = f"Stop {program_name}"
open_log_folder_shortcut_name: str | None = f"{program_name} - Logs"
open_crash_log_folder_shortcut_name: str | None = f"{program_name} - Crash Logs"
open_main_py_shortcut_name: str | None = f"{program_name} - Edit Code"
# ---------------------------------------
# Where else to put shortcuts (the project folder always gets all enabled ones).
# Setup removes shortcuts it created earlier that are no longer wanted.
# Start Menu: a folder named after program_name with all enabled shortcuts.
start_menu_shortcuts = True
# Desktop: list of shortcut kinds, from "terminal", "no_terminal", "stop", "settings",
# "logs", "crash_logs", "main_py". Example: ["no_terminal"]
desktop_shortcuts: list[str] = []
# ---------------------------------------
# String added before prints/inputs. Accepts datetime.datetime.strftime usage: e.g. "%H:%M:%S | ". None to turn off:
print_prepend: str | None = "%H:%M:%S | "
input_prepend: str | None = "%H:%M:%S > "
# ---------------------------------------
# Start script in script folder or folder of the starting shortcut. (affects log_path_is_relative_to_start_folder_if_relative setting below):
start_in_shortcut_folder = False
# ---------------------------------------
start_minimized = False
# ---------------------------------------
# What to do when the program is started while it is already running:
#   "allow"    start another instance
#   "focus"    bring the running instance's window to the front instead (asks to replace it if it has no window)
#   "prevent"  show a message and do not start
#   "replace"  stop the running instance(s), then start
#   "ask"      ask whether to replace the running instance(s)
instance_policy = "allow"
# ---------------------------------------
# Stop shortcut and instance_policy "replace": seconds a running instance gets to close by itself
# (its windows receive a normal close request, a console app gets Ctrl+C) before it is terminated.
# 0 terminates immediately.
stop_timeout_seconds: float = 5
# ---------------------------------------

# ======================================
# ==== Python and Package Settings ====
# ======================================

# ---------------------------------------
# Packages the app needs: PyPI names with optional version limits, e.g. ["requests", "numpy>=2", "pillow==11.*"].
# The launcher installs exactly these, with the versions recorded in backend/uv.lock (commit that file).
# The dev tools add_packages, remove_packages and find_imports edit this list for you.
packages: list[str] = []
# ---------------------------------------
# [bootstrap] Where the app's Python comes from:
#   "local"                          uv installs it inside this project (code/backend/pythons). Portable.
#   "uv_user"                        uv installs it in its per-user folder, shared by projects.
#   "system_if_matching_else_local"  use an installed Python matching python_version, otherwise install locally.
#   "system_default_any_version"     use the default installed Python (py launcher / PATH), whatever its version.
#                                    Falls back to a local install of python_version if none is found.
python_source = "uv_user"
# ---------------------------------------
# [bootstrap] Where the app's packages live:
#   "project_venv"               a uv-managed virtual environment in code/backend/.venv (recommended)
#   "interpreter_site_packages"  the selected interpreter's own packages (only with the "system_..." sources)
package_environment = "project_venv"
# ---------------------------------------
# [bootstrap] uv itself:
#   uv_prefer: which uv to use when both a global (on PATH) and a local (code/backend/uv) uv exist: "global" | "local"
#   uv_install_if_missing: "global" (Astral's installer, adds uv to your user PATH) | "local" | "never"
#   uv_version: "" for the latest, an exact version like "0.11.32", or a range like ">=0.9,<1"
#   A global uv that does not satisfy uv_version is not changed; a local uv is installed instead.
uv_prefer = "global"
uv_install_if_missing = "global"
uv_version = ""
# ---------------------------------------
# [bootstrap] For python_source = "uv_user": also register the Python in Windows (py launcher) and put python3.x.exe on PATH:
uv_user_python_visible_globally = True
# ---------------------------------------
# [bootstrap] uv download cache: "global" (uv's per-user cache) or "local" (code/backend/uv-cache, grows over time):
uv_cache = "global"
# ---------------------------------------
# [bootstrap] Allow normal launches to download uv, Python or packages. Setup and dev tools may always download.
# False makes launches fail with a clear message instead of using the network.
allow_downloads_at_launch = True
# ---------------------------------------
# [bootstrap] Use Windows' certificate store for downloads (needed behind some company proxies):
use_system_certificates = False
# ---------------------------------------
# package_environment = "interpreter_site_packages": allow the missing-package menu to install into that interpreter:
allow_installing_into_global_python = False
# ---------------------------------------
# Prepare uv, Python and packages when running Setup instead of on the first start:
install_environment_when_generating_shortcuts = True
# ---------------------------------------

# ==========================
# ==== Logging Settings ====
# ==========================

# ---------------------------------------
# Logging redirects stdout/stderr to pipes. Disable terminal logging if the app needs real console handles/a TTY.
enable_log_for_terminal_start = True
enable_log_for_no_terminal_start = True
# if overwrite is False it will append instead if a file with that name exists:
# Unique run suffixes normally give each launch a separate file, regardless of this flag.
overwrite_log = True
# decide if log path (below) is relative to start folder (where shortcut is started) or to this file:
log_path_is_relative_to_start_folder_if_relative = False
# Accepts datetime.datetime.strftime usage (e.g. "log_%Y-%m-%d_%H-%M-%S.txt"). None to disable:
# After changing the folder, run Setup again (the Logs shortcut opens it) and update the root .gitignore's /logs/* rule.
log_path: str | None = "..\\..\\logs\\log_%Y-%m-%d_%H-%M-%S.txt"
# ---------------------------------------
log_print_prepend: str | None = "%H:%M:%S | "
log_input_prepend: str | None = "%H:%M:%S > "
# ---------------------------------------
# Crash logging behavior:
# if overwrite is False it will append instead if a file with that name exists:
# Crash reports also receive unique run suffixes rather than sharing one file across launches.
overwrite_crash_log = True
# decide if crash log path (below) is relative to start folder (where shortcut is started) or to this file:
crash_log_path_is_relative_to_start_folder_if_relative = False
# Accepts datetime.datetime.strftime usage (e.g. "log_%Y-%m-%d_%H-%M-%S.txt"). None to disable:
# After changing the folder, run Setup again (the Crash Logs shortcut opens it) and update the root .gitignore's /crash logs/* rule.
crash_log_path: str | None = "..\\..\\crash logs\\crash_log_%Y-%m-%d_%H-%M-%S.txt"
# ---------------------------------------
# Retention: keep the logs of at most this many runs in each log folder (None keeps everything):
max_log_files: int | None = None
# Delete per-run diagnostic folders (DONT_CHANGE/tmp/runs) older than this many days (None keeps them):
max_run_folder_age_days: int | None = None
# ---------------------------------------

# =======================================
# ==== Program Finish/Crash Settings ====
# =======================================

# ---------------------------------------
# Program exit behavior:
# success = sys.exit(0)/sys.exit()/file-end
# failure = sys.exit(non-zero) or an unhandled exception
# crash   = python interpreter crash (aka where even try/except fails)
# keyboard_interrupt = user presses CTRL+C (KeyboardInterrupt)
# ---------------------------------------
close_after_success = True
close_after_failure = False
close_after_crash = False
close_after_keyboard_interrupt = False
# ---------------------------------------
open_log_file_after_success = False
open_log_file_after_failure = False
open_log_file_after_crash = False
open_log_file_after_keyboard_interrupt = False
# ---------------------------------------
open_main_py_after_success = False
open_main_py_after_failure = False
open_main_py_after_crash = False
open_main_py_after_keyboard_interrupt = False
# ---------------------------------------
# False for off. True for default. String for rel. path to .wav in C:\Windows\Media:
play_sound_after_success: str | bool = False
play_sound_after_failure: str | bool = True
play_sound_after_crash: str | bool = True
play_sound_after_keyboard_interrupt: str | bool = False
# ---------------------------------------
# None to disable change
title_after_success: str | None = f"[Finished] {program_name}"
title_after_failure: str | None = f"[Failure] {program_name}"
title_after_crash: str | None = f"[Crash] {program_name}"
title_after_keyboard_interrupt: str | None = f"[KeyboardInterrupt] {program_name}"
# ---------------------------------------
# Terminal colors after the program finishes (None or "" keeps the current colors):
# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,7=White,8=Gray,9=LightBlue
# Text color: A=LightGreen,B=LightAqua,C=LightRed,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_colors_after_success: str | None = "2F"
terminal_colors_after_failure: str | None = "4F"
terminal_colors_after_crash: str | None = "4F"
terminal_colors_after_keyboard_interrupt: str | None = "6C"
# ---------------------------------------

# ============================
# ==== Traceback Settings ====
# ============================

# Datetime format shown in crash reports:
error_date_format = "%Y-%m-%d %H:%M:%S"
# Source lines of your own code shown before and after each failing line (0 for none).
# Library code always shows just the failing line, like Python does.
traceback_lines_before: int = 3
traceback_lines_after: int = 3
# Color tracebacks in the terminal (log files are always plain text):
traceback_colors = True

# =======================
# ==== Icon Settings ====
# =======================

# Configure every generated sub-icon separately. ``scale`` is the fraction of
# the base icon area it covers (0 < value <= 1); ``alignment`` accepts compass
# positions such as "bottom right", "top", or "center left". Set *either*
# variable in a pair to ``None`` to generate that icon without its sub-icon.
settings_sub_icon_scale: float | None = 0.35
settings_sub_icon_alignment: str | None = "bottom right"
stop_sub_icon_scale: float | None = 0.35
stop_sub_icon_alignment: str | None = "bottom right"
log_sub_icon_scale: float | None = 0.35
log_sub_icon_alignment: str | None = "bottom right"
success_sub_icon_scale: float | None = 0.35
success_sub_icon_alignment: str | None = "bottom right"
failure_sub_icon_scale: float | None = 0.35
failure_sub_icon_alignment: str | None = "bottom right"
crash_log_sub_icon_scale: float | None = 0.35
crash_log_sub_icon_alignment: str | None = "bottom right"
open_main_py_sub_icon_scale: float | None = 0.35
open_main_py_sub_icon_alignment: str | None = "bottom right"

# =================================
# ==== Less Important Settings ====
# =================================

# ---------------------------------------
# Application arguments passed to main.py:
args_for_main_py: list[str] = []
# ---------------------------------------

# =========================================
# ==== Launcher Mode Specific Settings ====
# =========================================

# ---------------------------------------
# use_classic_terminal=True uses classic old-style terminal (conhost.exe) with no tabs (looks more like an app and less like a terminal but text rendering and zooming are worse).
# use_classic_terminal=False uses modern Windows Terminal (wt.exe): tabs and modern text rendering and zoom.
# Falls back to the classic terminal with a warning if Windows Terminal is not installed.
use_classic_terminal = True
# ---------------------------------------

# settings for use_classic_terminal = True/False:
# ---------------------------------------
# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,7=White,8=Gray,9=LightBlue:
terminal_bg_color: str | None = "9"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_text_color: str | None = "F"
# ---------------------------------------

# settings for use_classic_terminal = False:
# ---------------------------------------
# Terminal tab bar color in modern terminal. None uses the Windows Terminal profile default (e.g. "#3B78FF"):
tab_bar_color: str | None = "#3B78FF"
# ---------------------------------------

# ---------------------------------------
# open this file if someone runs it directly (e.g. double-clicks it in Explorer) instead of running the launcher:
if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backend.DONT_CHANGE.scripts.console_tools import open_in_editor

    open_in_editor(str(Path(__file__).resolve()))

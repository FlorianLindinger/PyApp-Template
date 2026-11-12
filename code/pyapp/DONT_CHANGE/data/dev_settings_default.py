"""Developer settings: the program's identity, Python and packages, logging, and what happens when it ends.

Start at IMPORTANT; most projects never need to go further.
Relative paths in this file are interpreted as relative to this file.

Settings marked [bootstrap] are also read by the Windows bootstrap before any Python
exists. Keep each of them on ONE line as a plain literal ("text", True, False):
no expressions, f-strings or line continuations.
"""

# fmt:off
# ruff: noqa: I001,UP006,UP007,UP035,UP045,S603,PTH100,RUF100
# For backward compatibility down to Python 3.8:
from __future__ import annotations
from typing import Dict, List
# fmt:on
# ==================================================================

# IMPORTANT:
#   what almost every project sets: name, Python, packages, logging on/off, running twice.
# MEDIUM:
#   behavior you sometimes want different: program end, window, start and stop, log files.
# LOW:
#   special cases and cosmetics: shortcut names, uv, certificates, error report details.

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

# Packages the app needs, one per line between the triple quotes, like a requirements.txt: PyPI names with optional
# version limits such as numpy>=2 or pillow==11.*; # comments and --hash options are fine.
# Only strings are accepted; use "" for no packages.
# The launcher installs exactly these, with the versions recorded in pyapp/generated/uv.lock (commit that file).
# A package removed here stays installed until you run the dev tool sync_packages.
# The dev tools add_packages, remove_packages and find_imports edit this for you.
packages = """

# Copy-paste needed packages here

"""
# A requirements file whose packages are installed in addition to "packages" (relative to this file), e.g.
# "..\\requirements.txt"; The launcher only reads it: the dev tools change "packages", so a package
# from this file is removed in the file itself. A package may not be in both places. "" to disable.
requirements_path = ""


# --- Logging and prints ---
# Write a log file (location: log_path below). Logging turns stdout/stderr into pipes,
# so turn the terminal one off if the app needs a real console (TTY):
enable_log_for_terminal_start = True
# Without a terminal, the log is the only place where prints end up:
enable_log_for_no_terminal_start = True

# Text added before each print and input in the window. Accepts strftime codes, e.g. "%H:%M:%S | ". "" to disable.
print_prepend = "%H:%M:%S | "
input_prepend = "%H:%M:%S > "

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
# The browser terminal shortcut (browser_terminal_shortcut_name) shows the console as a terminal in a new tab of your
# default browser instead, with the same input, Ctrl+C, colors and titles: sharp text, zoom with Ctrl+wheel or
# Ctrl+/-, clickable links, copy and paste like Windows Terminal. Closing the tab ends the program, like closing a
# console window. Needs Windows 10 1809 or newer.
# Its address stays the same, so it can be bookmarked (works while the program runs); Setup shows it.
#   ""  automatic: http://<program name>.localhost:<port of this project folder>/<key>/
#   e.g. "http://my-app.localhost:8765" or "http://127.0.0.1:8765" (the key is added; it is kept per PC
#   in pyapp/generated and never committed). Setup also registers the start link <program name>://start,
#   which starts the program in the browser terminal, e.g. from a bookmark.
browser_terminal_address = ""

# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,7=White,8=Gray,9=LightBlue. "" for default:
terminal_bg_color = "9"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,D=LightPurple,E=LightYellow,F=BrightWhite. "" for default:
terminal_text_color = "F"

# --- Starting and stopping ---
# The Python file the launcher runs. It must be inside the code folder, but not in code/pyapp.
# Imports start from its folder, like `python main.py`. Run Setup again after changing it (for the Edit Code shortcut).
main_script_path = "..\\main.py"

# String arguments passed to main.py:
args_for_main_py: List[str] = []

# Environment variables set for main.py, e.g. {"MY_SETTING": "1"}.
# PYTHON* variables have no effect on main.py itself, because it runs with -E.
environment_for_main_py: Dict[str, str] = {}

# Working folder of the program. False: the folder of the main script. True: the folder of the starting shortcut.
start_in_shortcut_folder = False

# Stop shortcut and instance_policy "replace": seconds a running instance gets to close by itself
# (its windows receive a normal close request, a console app gets Ctrl+C) before it is terminated.
# 0 terminates immediately.
stop_timeout_seconds: float = 3

# --- Where uv and Python come from ---
# The dev tool make_self_contained sets these three to "local" and puts uv, Python and all packages into
# code/pyapp/generated: the folder then runs on other PCs without internet or installing anything.
# More uv settings: see "uv" further down.
# [bootstrap] Where the app's Python comes from:
#   "local"    uv installs it inside this project (code/pyapp/generated/pythons).
#   "uv_user"  uv installs it in its per-user folder, shared by projects.
#   "system"   a Python already installed on this PC, e.g. by your IT department. Nothing is downloaded.
python_source = "uv_user"
# [bootstrap] Which uv to use when both a global (on PATH) and a local (code/pyapp/generated/uv) uv exist: "global" | "local"
uv_prefer = "global"
# [bootstrap] Where uv is installed when none is found: "global" (for your Windows user, added to your user PATH) | "local" | "never"
uv_install_if_missing = "global"

# --- Settings file and shortcut locations ---
# File that the Settings shortcut opens, for the people using the app (any file type; "" to disable).
# Run Setup again after changing it:
user_settings_path = "..\\settings.py"

# The project folder always gets all enabled shortcuts. Setup removes earlier ones that are no longer wanted.
# Start Menu: a folder named after program_name with all enabled shortcuts:
start_menu_shortcuts = True
# Desktop: a list of "terminal", "no_terminal", "browser_terminal", "stop", "settings", "logs", "crash_logs", "open_code". Example: ["no_terminal"]
desktop_shortcuts: List[str] = []

# --- Log files ---
# Accepts strftime codes, e.g. "log_%Y-%m-%d_%H-%M-%S.txt". "" to disable.
# After changing the folder, run Setup again (the Logs shortcut opens it) and update the root .gitignore's /logs/* rule.
log_path = "..\\..\\logs\\log_%Y-%m-%d_%H-%M-%S.txt"
# A relative log_path starts at: False = this file, True = the folder of the starting shortcut.
log_path_is_relative_to_start_folder_if_relative = False

# Text added before each print and input in the log file (same format as print_prepend):
log_print_prepend = "%H:%M:%S | "
log_input_prepend = "%H:%M:%S > "

# --- Crash logs ---
# A text file with the error report, written after every failure and after Ctrl+C. It also has everything the app printed, if logging is on.
enable_crash_log = True
# Accepts strftime codes, e.g. "crash_log_%Y-%m-%d_%H-%M-%S.txt". "" to disable.
# After changing the folder, run Setup again (the Crash Logs shortcut opens it) and update the root .gitignore's /crash logs/* rule.
crash_log_path = "..\\..\\crash logs\\crash_log_%Y-%m-%d_%H-%M-%S.txt"
# A relative crash_log_path starts at: False = this file, True = the folder of the starting shortcut.
crash_log_path_is_relative_to_start_folder_if_relative = False

# ==================================================================
# ==== LOW =========================================================
# ==================================================================

# --- Shortcut names ---
# Shortcut names. "" to disable.
terminal_shortcut_name = f"{program_name}"
no_terminal_shortcut_name = f"{program_name} (no Terminal)"
browser_terminal_shortcut_name = f"{program_name} (Browser)"
open_settings_shortcut_name = f"{program_name} - Settings"
stop_running_shortcut_name = f"Stop {program_name}"
open_log_folder_shortcut_name = f"{program_name} - Logs"
open_crash_log_folder_shortcut_name = f"{program_name} - Crash Logs"
open_code_shortcut_name = f"{program_name} - Edit Code"

# --- Startup ---
# Start with the window minimized:
start_minimized = False

# --- uv ---
# uv_prefer and uv_install_if_missing: see "Where uv and Python come from" above.
# [bootstrap] uv_version: "" for the latest, an exact version like "0.11.32", or a range like ">=0.9,<1"
#   A global uv that does not satisfy uv_version is not changed; a local uv is installed instead.
#   If that uv cannot provide python_version, the newest uv is downloaded to %LOCALAPPDATA%\PyApp-Template\uv and used
#   from then on. It is not put on PATH, so your global uv stays the default. uv_install_if_missing = "never" or an exact
#   uv_version turns this off.
uv_version = ""

# [bootstrap] For python_source = "uv_user": also register the Python in Windows (py launcher) and put python3.x.exe on PATH:
uv_user_python_visible_globally = True

# [bootstrap] uv download cache: "global" (uv's per-user cache) or "local" (code/pyapp/generated/uv-cache, grows over time):
uv_cache = "global"

# [bootstrap] Use Windows' certificate store for downloads (needed behind some company proxies):
use_system_certificates = False

# --- GitHub ---
# GitHub Actions for this app; Setup creates or removes their files in .github/workflows:
#   "leaks"    on every push and PR to main: look for secrets and personal data
github_actions: List[str] = []

# --- Error reports ---
# Date format in crash reports:
error_date_format = "%Y-%m-%d %H:%M:%S"

# --- Windows Terminal only (use_classic_terminal = False) ---
# Tab bar color, e.g. "#3B78FF". "" for Windows default.
tab_bar_color = "#3B78FF"

# ==================================================================

# open this file if someone runs it directly (e.g. double-clicks it in Explorer) instead of running the launcher:
if __name__ == "__main__":
    import os
    import shutil
    import subprocess

    # VS Code if it is on PATH, otherwise Notepad. "code" is a .cmd file, so the command is one quoted string.
    editor = shutil.which("code") or "notepad.exe"
    subprocess.Popen(f'"{editor}" "{os.path.abspath(__file__)}"')

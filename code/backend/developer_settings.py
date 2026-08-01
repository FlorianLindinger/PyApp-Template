"""WIP

Relative paths in this file are interpreted as relative to this file."""

# =========================
# ==== Settings Overview ====
# =========================

# 1. Important Settings: program name, Python version, shortcuts, startup, and console prefixes.
# 2. Logging Settings: normal and crash-log locations and behavior.
# 3. Program Finish/Crash Settings: what happens after success, failure, crashes, and KeyboardInterrupt.
# 4. Traceback Settings: displayed crash-report date format and Rich color theme.
# 5. Icon Settings: individual overlay size and alignment for generated shortcut icons.
# 6. Less Important Settings: process, Python installation, package, and startup behavior.
# 7. Launcher Mode Specific Settings: classic-console and Windows Terminal appearance.

# ============================
# ==== Important Settings ====
# ============================

# ---------------------------------------
# Name of this program:
program_name = "PyApp-Template"
# ---------------------------------------
# Python version (""/"x"/"x.y"/"x.y.z"). Finds latest matching(msi-install-available) Python version ("" == latest):
python_version: str = "3.14"
# ---------------------------------------
# Path to end-user settings file (None to disable). File type can be anything openable by vscode/editor:
user_settings_path: str | None = "..\\settings.py"
# ---------------------------------------
# Names of created shortcuts (None to disable). Accepts for example f"{program_name}":
windows_terminal_shortcut_name: str | None = f"{program_name}"
no_terminal_shortcut_name: str | None = f"{program_name} (no Terminal)"
open_settings_shortcut_name: str | None = f"{program_name} - Settings"
stop_running_shortcut_name: str | None = f"Stop {program_name}"
open_log_folder_shortcut_name: str | None = f"{program_name} - Logs"
open_crash_log_folder_shortcut_name: str | None = f"{program_name} - Crash Logs"
open_main_py_shortcut_name: str | None = f"{program_name} - Open main.py"
# ---------------------------------------
# String added before prints/inputs. Accepts datetime.datetime.strftime usage: e.g. "%H:%M:%S | ". None to turn off:
print_prepend: str | None = "%H:%M:%S | "
input_prepend: str | None = "%H:%M:%S > "
# ---------------------------------------
# Start script in scipt folder or folder of the starting shortcut. (affects log_path_rel_to_start_folder setting below):
start_in_shortcut_folder = False
# ---------------------------------------
start_minimized = False
# ---------------------------------------

# ==========================
# ==== Logging Settings ====
# ==========================

# ---------------------------------------
enable_log_for_Windows_terminal_start = True
enable_log_for_no_terminal_start = True
# if overwrite is False it will append instead if a file with that name exists:
overwrite_log = True
# decide if log path (below) is relative to start folder (where shortcut is started) or to this file:
log_path_is_relative_to_start_folder_if_relative = False
# Accepts datetime.datetime.strftime usage (e.g. "log_%Y-%m-%d_%H-%M-%S.txt"). None to disable:
log_path: str | None = "..\\..\\logs\\log_%Y-%m-%d_%H-%M-%S.txt"
# ---------------------------------------
log_print_prepend: str | None = "%H:%M:%S | "
log_input_prepend: str | None = "%H:%M:%S > "
# ---------------------------------------
# Crash logging behavior:
# if overwrite is False it will append instead if a file with that name exists:
overwrite_crash_log = True
# decide if crash log path (below) is relative to start folder (where shortcut is started) or to this file:
crash_log_path_is_relative_to_start_folder_if_relative = False
# Accepts datetime.datetime.strftime usage (e.g. "log_%Y-%m-%d_%H-%M-%S.txt"). None to disable:
crash_log_path: str | None = "..\\..\\crash logs\\crash_log_%Y-%m-%d_%H-%M-%S.txt"
# ---------------------------------------

# =======================================
# ==== Program Finish/Crash Settings ====
# =======================================

# ---------------------------------------
# Program exit behavior:
# success = sys.exit(0)/sys.exit()/file-end
# failure = sys.exit(not-a-zero) e.g. raised Exception.Exception
# crash   = python interpreter crash (aka where even try/except fails)
# KeyboardInterrupt = user presses CTRL+C
# ---------------------------------------
close_after_success = True
close_after_failure = False
close_after_crash = False
close_after_KeyboardInterrupt = False
# ---------------------------------------
open_log_file_after_success = False
open_log_file_after_failure = False
open_log_file_after_crash = False
open_log_file_after_KeyboardInterrupt = False
# ---------------------------------------
open_main_py_after_success = False
open_main_py_after_failure = False
open_main_py_after_crash = False
open_main_py_after_KeyboardInterrupt = False
# ---------------------------------------
# False for off. True for default. String for rel. path to .wav in C:\Windows\Media:
play_sound_after_success: str | bool = False
play_sound_after_failure: str | bool = True
play_sound_after_crash: str | bool = True
play_sound_after_KeyboardInterrupt: str | bool = False
# ---------------------------------------
# None to disable change
title_after_success: str | None = f"[Finished] {program_name}"
title_after_failure: str | None = f"[Failure] {program_name}"
title_after_crash: str | None = f"[Crash] {program_name}"
title_after_KeyboardInterrupt: str | None = f"[KeyboardInterrupt] {program_name}"
# ---------------------------------------
# Terminal colors after the program finishes (None or "" keeps the current colors):
# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,8=Gray,7=White,9=LightBlue
# Text color: A=LightGreen,B=LightAqua,C=LightRed,,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_colors_after_success: str | None = "2F"
terminal_colors_after_failure: str | None = "4F"
terminal_colors_after_crash: str | None = "4F"
terminal_colors_after_KeyboardInterrupt: str | None = "6C"
# ---------------------------------------

# ============================
# ==== Traceback Settings ====
# ============================

# Datetime format shown in crash reports:
PRINTED_ERROR_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# Include local variables in Rich traceback output. This can expose sensitive values.
show_traceback_locals: bool = False
# Number of source-code lines shown before and after the failing line.
traceback_extra_lines: int = 3
# Colors/styles used by Rich traceback output:
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

# ============================
# ==== Icon Settings ====
# ============================

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
crash_sub_icon_scale: float | None = 0.35
crash_sub_icon_alignment: str | None = "bottom right"
crash_log_sub_icon_scale: float | None = 0.35
crash_log_sub_icon_alignment: str | None = "bottom right"
open_main_py_sub_icon_scale: float | None = 0.35
open_main_py_sub_icon_alignment: str | None = "bottom right"
keyboardInterrupt_sub_icon_scale: float | None = 0.35
keyboardInterrupt_sub_icon_alignment: str | None = "bottom right"

# =================================
# ==== Less Important Settings ====
# =================================

# ---------------------------------------
# How to treat alredy running program instances:
prevent_start_if_already_running = False
close_already_running_instances_on_start = False
prompt_to_close_existing_instances = False
# ---------------------------------------
# Decide if global default (any version) Python should be used instead of automatic localized download and installation of Python/packages:
use_global_python = False
# ---------------------------------------
# Install Python environment while generating shortcuts instead of for first start (Ignored when use_global_python = True):
install_python_when_generating_shortcuts = True
# ---------------------------------------
# Unminimize and forground program on first print:
highlight_window_on_first_print = False
# supress keyboard interrupt (CTRL+C):
supress_keyboard_interrupt = False
# args passed to main script:
args_for_main_py: list[str] = []
# ---------------------------------------
# Decide what parts of vanilla full Python to install:
# --
#   Tkinter (Required for Tk-based GUIs or IDLE and used as default backend for matplotlib.pyplot. ~11 MB):
install_tkinter = True
#   Test suite (Needed for interpreter testing. ~31 MB):
install_tests = False
#   Tools folder: Needed for: Language translation workflows/Python's code demos/old editors/old exe converters. (~1 MB, some installation time):
install_tools = False
# ---------------------------------------
# Use uv (faster replacement of pip) to install packages (it uses global uv if available and installs locally otherwise):
use_uv_to_install_packages = True
# ---------------------------------------

# =========================================
# ==== Launcher Mode Specific Settings ====
# =========================================

# --------------------------------
# ---- Windows Terminal Start ----
# --------------------------------

# ---------------------------------------
# use_classic_terminal=True uses classic old-style terminal (conhost.exe) with no tabs (looks more like an app and less like a terminal but text rendering and zooming are worse).
# use_classic_terminal=False uses modern Windows Terminal (wt.exe): tabs and modern text rendering and zoom:
use_classic_terminal = True
# ---------------------------------------

# settings for use_classic_terminal = True/False:
# ---------------------------------------
# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,8=Gray,7=White,9=LightBlue:
terminal_bg_color: str | None = "9"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_text_color: str | None = "F"
# ---------------------------------------

# settings for use_classic_terminal = False:
# ---------------------------------------
# Terminal tab bar color in modern terminal. None uses the Windows Terminal profile default (e.g. "#3B78FF"):
tab_bar_color: str | None = "#3B78FF"
# ---------------------------------------

# =========================================

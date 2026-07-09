"""WIP"""

# ============================
# ==== Important Settings ====
# ============================

# -------------------------------------------------
# Name of this program:
program_name = "PyApp-Template"
# -------------------------------------------------
# Python version (""/"x"/"x.y"/"x.y.z"). Finds latest matching(msi-install-available) Python version ("" == latest):
python_version: str = "3.14"
# -------------------------------------------------
# Path to end-user settings file (None to disable). File type can be anything openable by vscode/editor:
user_settings_path: str | None = "..\\settings.py"
# -------------------------------------------------
# Names of created shortcuts (None to disable). Accepts for example f"{program_name}":
windows_terminal_shortcut_name: str | None = f"{program_name}"
no_terminal_shortcut_name: str | None = f"{program_name} (no Terminal)"
open_settings_shortcut_name: str | None = f"{program_name} - Settings"
stop_running_shortcut_name: str | None = f"Stop {program_name}"
open_log_shortcut_name: str | None = f"{program_name} - Log"
# -------------------------------------------------
# String added before prints/inputs. Accepts datetime.datetime.strftime usage: e.g. "%H:%M:%S | ". None to turn off:
print_prepend: str | None = "%H:%M:%S | "
input_prepend: str | None = "%H:%M:%S > "
log_print_prepend: str | None = "%H:%M:%S | "
log_input_prepend: str | None = "%H:%M:%S > "
# -------------------------------------------------
# Program exit behavior:
# success = sys.exit(0)/sys.exit()/file-end
# failure = sys.exit(not-a-zero) e.g. raised Exception.Exception
# crash   = python interpreter crash (aka where even try/except fails)
# KeyboardInterrupt = user presses CTRL+C
close_after_success = True
close_after_failure = False
close_after_crash = False
close_after_KeyboardInterrupt = False
open_log_file_after_success = False
open_log_file_after_failure = False
open_log_file_after_crash = False
open_log_file_after_KeyboardInterrupt = False
# False for off. True for default. String for rel. path to .wav in C:\Windows\Media:
play_sound_after_success: str | bool = False
play_sound_after_failure: str | bool = True
play_sound_after_crash: str | bool = True
play_sound_after_KeyboardInterrupt: str | bool = False
# -------------------------------------------------
# Start script in scipt folder or folder of the starting shortcut. (affects log_path_rel_to_start_folder setting below):
start_in_shortcut_folder = False
# -------------------------------------------------
# Logging behavior:
enable_log_for_Windows_terminal_start = True
enable_log_for_no_terminal_start = True
overwrite_log = True
# Accepts datetime.datetime.strftime usage: e.g. "log_%Y_%m_%d". Affected by start_in_shortcut_folder setting above. None to disable:
log_path_rel_to_start_folder: str | None = "..\\..\\logs\\log_%Y_%m_%d.txt"
# ------------------------------------------------

# =================================
# ==== Less Important Settings ====
# =================================

# -------------------------------------------------
# How to treat alredy running program instances:
prevent_start_if_already_running = False
close_already_running_instances_on_start = False
prompt_to_close_existing_instances = False
# -------------------------------------------------
# Decide if global default (any version) Python should be used instead of automatic localized download and installation of Python/packages:
use_global_python = False
# -------------------------------------------------
# Install Python environment while generating shortcuts instead of for first start (Ignored when use_global_python = True):
install_python_when_generating_shortcuts = True
# -------------------------------------------------
# Unminimize and forground program on first print:
highlight_window_on_first_print = False
# supress keyboard interrupt (CTRL+C):
supress_keyboard_interrupt = False
# args passed to main script:
args_for_main_py = []
# -------------------------------------------------
# Decide what parts of vanilla full Python to install:
# --
#   Tkinter (Required for Tk-based GUIs or IDLE and used as default backend for matplotlib.pyplot. ~11 MB):
install_tkinter = True
#   Test suite (Needed for interpreter testing. ~31 MB):
install_tests = False
#   Tools folder: Needed for: Language translation workflows/Python's code demos/old editors/old exe converters. (~1 MB, some installation time):
install_tools = False
# -------------------------------------------------
# Use uv to install packages 

# =========================================
# ==== Launcher Mode Specific Settings ====
# =========================================

# --------------------------------
# ---- Windows Terminal Start ----
# --------------------------------

# use_classic_terminal=True uses classic old-style terminal (conhost.exe) with no tabs (looks more like an app and less like a terminal but text rendering and zooming are worse).
# use_classic_terminal=False uses modern Windows Terminal (wt.exe): tabs and modern text rendering and zoom:
use_classic_terminal = True
# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,8=Gray,7=White,9=LightBlue:
terminal_bg_color: str | None = "9"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_text_color: str | None = "F"


start_minimized = False
start_maximized = False

disable_resize = False
always_on_top = False


# --------------------------------

# dont resize
# ontop

hide_title_bar = False
disable_minimize_button = False
disable_maximize_button = False
disable_x_button = False


# --------------------------------

# Terminal tab bar color. None uses the Windows Terminal profile default (e.g. "#3B78FF"):
tab_bar_color: str | None = "#3B78FF"

# --------------------------------

# =========================================

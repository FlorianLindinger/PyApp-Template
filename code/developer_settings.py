# ============================
# ==== important settings ====
# ============================

# -------------------------------------------------
# Name of this program:
program_name = "PyApp-Template"
# -------------------------------------------------
# Python version. Can be in format "x"/"x.y"/"x.y.z". Finds latest (msi-install-available) Python version compatible with this setting. Empty string "" gives latest (not recommended if you want to make sure the code works always the same):
python_version: str = "3.14"
# -------------------------------------------------
# Decide if global python (python & packages need to be installed manually on PC) should be used instead of automatic localized download and installation of all.
use_global_python = False
# -------------------------------------------------
# Decide working directory behavior:
# True  = Start in the folder where the shortcut is located
# False = Start in the "code" folder where the main scrip is
start_in_shortcut_folder = False
# -------------------------------------------------
print_timestamp_format: str | None = "%H:%M:%S | "
# None for no timestamps (else see datetime.datetime.strftime usage: e.g. "%H:%M:%S | ")
# ------------------------------------------------
ship_compiled_fancy_terminal_emulator = True
# ------------------------------------------------
#
# =================================
# ==== less important settings ====
# =================================

# -------------------------------------------------
# Names of generated shortcuts:
# (set to None to disable generation of specific shortcut. You can use program_name variable like since this is a python script)
start_windows_terminal_shortcut_name: str | None = f"{program_name}"  # start program with terminal
start_terminal_emulator_shortcut_name: str | None = f"{program_name} (Terminal Emulator)"  # start program with terminal emulator
start_browser_shortcut_name: str | None = f"{program_name} (Browser)"  # start program in default browser
start_no_terminal_shortcut_name: str | None = f"{program_name} (no Terminal)"  # start program without terminal
settings_shortcut_name: str | None = f"{program_name} - Settings"  # open settings file
stop_shortcut_name: str | None = f"Stop {program_name}"  # stop all started programs
# -------------------------------------------------
# success = sys.exit(0) or sys.exit() or no exit line.
close_on_success = True
play_sound_on_success: str | bool = False # False for no sound, True for default sound (notify.wav) or a path to a wav file relative to C:\Windows\Media\.
send_Windows_notification_on_success = True
# ----
# failure = normal failure exit codes (i.e. exit_code != 0), usually via "sys.exit(exit_code)" or raised error.
close_on_failure = False
play_sound_on_failure: str | bool  = True # False for no sound, True for default sound ("Windows Critical Stop.wav") or a path to a wav file relative to C:\Windows\Media\.
send_Windows_notification_on_failure = True
# ----
# crash of python interpreter is usually caused by code causing Windows to kill Python and won't be caught by try/except.
close_on_python_interpreter_crash = False
play_sound_on_python_interpreter_crash:str|bool  = True # False for no sound, True for default sound ("Windows Critical Stop.wav") or a path to a wav file relative to C:\Windows\Media\.
send_Windows_notification_on_python_interpreter_crash = True
# -------------------------------------------------
# Path of end-user settings file (file can be deleted)
user_settings_path: str | None = "settings.py"  # set None to not use. Can also be not python file.
# -------------------------------------------------
# Text shown before user input when input is echoed in the terminal.
input_prepend: str | None = "> "
# -------------------------------------------------
# Name of Python code file and has to be in "code" folder.
python_code_name = "main_code.py"
# -------------------------------------------------
script_after_python_interpreter_crash_name: str | None = "after_python_crash_code.py"
# Script has to be in "code" folder. You can use the same name as python_code_name setting here. Note that the last argument will indicate that it was launched as a after-interpreter-crash script. You can test this in script via sys.argv[-1]=="crash". Set it to None to not launch anything after a interpreter crash.
# -------------------------------------------------
ship_backend_python_and_backend_packages = True
# -------------------------------------------------
start_minimized = False
# -------------------------------------------------

# ==========================
# ==== logging settings ====
# ==========================

# -------------------------------------------------
log_path_rel_to_wdir: str | None = r"..\logs\log_%Y_%m_%d.txt"
# wdir is influenced by "start_in_shortcut_folder" setting. Can also be an absolute path and can accept datetime formatting (see datetime.datetime.strftime usage: e.g. "log_%Y_%m_%d.txt"). Set to None to disable logging to file.
# -------------------------------------------------
overwrite_log = True
# -------------------------------------------------
enable_log_for_terminal_start = True
enable_log_for_no_terminal_start = True
# -------------------------------------------------
log_timestamp_format = "%H:%M:%S | "
# None for no timestamps (else see datetime.datetime.strftime usage: e.g. "%H:%M:%S | ")
# -------------------------------------------------

# ====================================
# ==== terminal (visual) settings ====
# ====================================

# --------------------------------------------------
# settings that apply to the Windows Terminal shortcut:
# --------------------------------------------------

# Terminal colors (set None for Windows default):
# Background: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,8=Gray,7=White,9=LightBlue
# Text: A=LightGreen,B=LightAqua,C=LightRed,,D=LightPurple,E=LightYellow,F=BrightWhite
terminal_bg_color: str | None = "9"
terminal_text_color: str | None = "F"
# -------------------------------------------------

# -------------------------------------------------
# settings that apply to the terminal emulator shortcut:
# -------------------------------------------------

terminal_needs_input = True
dark_mode: bool | None = True  # None = Windows dark setting
stylesheet_path: str | None = "terminal_stylesheet.py"  # None = default stylesheet settings
button_settings: None | list[tuple[str, dict[str, bool]]] = [  # None = default button settings
    # ("button_name", {"visible"/"clickable"/"pinned"/"unpin_able"/"starting_state": bool , ...}),
    ("show_input", {"pinned": False, "starting_state": True}),
    ("autoscroll", {"starting_state": True}),
    ("foreground_on_print", {"pinned": False}),
    ("highlight_on_print", {"pinned": False}),
    ("confirm_close", {"pinned": False}),
    ("restart", {}),
    ("clear", {}),
    ("stop", {"visible": True}),
    ("to_tray", {"clickable": True}),
    ("open_script", {"pinned": False}),
]
# -------------------------------------------------

# ==================================
# ==== least important settings ====
# ==================================

# -------------------------------------------------
use_faulthandler = True
# -------------------------------------------------
# Decide what parts of vanilla full Python install you actually need (enabling all is ~90 MB, disabling all is ~47 MB):
# ----
#   Include Tkinter GUI library? Required for Tk-based GUIs or IDLE and used as default backend for matplotlib.pyplot. (~11 MB):
install_tkinter = True
#   Include Python's internal test suite (Lib/test)? Only needed for interpreter testing. (~31 MB):
install_tests = False
#   Include Python's "Tools" folder? Needed for: Language translation workflows/Python's code demos/old editors/old exe converters. (~1 MB, some installation time):
install_tools = False
# -------------------------------------------------

# =======================
# ==== debug options ====
# =======================

use_uncompiled_terminal_emulator_and_run_it_in_global = False

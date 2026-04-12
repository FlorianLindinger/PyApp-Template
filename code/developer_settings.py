# ============================
# ==== important settings ====
# ============================

# -------------------------------------------------
# Name of the this program, the terminal, and shortcuts (white space allowed):
program_name = "PyApp-Template"
# -------------------------------------------------
# Python version. Can be in format "x"/"x.y"/"x.y.z". Finds latest (msi-install-available) Python version compatible with this setting. Empty string "" gives latest (not recommended if you want to make sure the code works always the same):
python_version = "3.13"
# -------------------------------------------------
# Decide if global python (python & packages need to be installed manually on PC) should be used instead of automatic localized download and installation of all.
use_global_python = False
# -------------------------------------------------
# Decide working directory behavior.
# True  = Start in the folder where the shortcut is located
# False = Start in the "code" folder
start_in_shortcut_folder = False
# -------------------------------------------------

# =================================
# ==== less important settings ====
# =================================

# -------------------------------------------------
# Path of user settings file (file can be deleted)
user_settings_path: str | None = "settings.py"  # set None to not use
# -------------------------------------------------
# Decide what parts of vanilla full Python install you actually need (enabling all is ~90 MB, disabling all is ~47 MB):
# -------------------------------------------------
#   Include Tkinter GUI library? Required for Tk-based GUIs or IDLE and used as default backend for matplotlib.pyplot. (~11 MB):
install_tkinter = True
#   Include Python's internal test suite (Lib/test)? Only needed for interpreter testing. (~31 MB):
install_tests = False
#   Include Python's "Tools" folder? Needed for: Language translation workflows/Python's code demos/old editors/old exe converters. (~1 MB, some installation time):
install_tools = False
# -------------------------------------------------
# Name of Python code file:
python_code_name = "main_code.py"
after_python_crash_code_name = "after_python_crash_code.py"
# -------------------------------------------------
# Names of generated shortcuts:
# (Delte or set =="" to disable generation of specific shortcut)
start_name = f"{program_name}"  # start program
start_no_terminal_name = f"{program_name} (with log & no terminal)"  # start program without terminal
settings_name = f"{program_name} - settings"  # open settings file
stop_no_terminal_name = f"stop (no-terminal) {program_name}"  # stop program that was started without terminal
# -------------------------------------------------
close_on_crash = False
close_on_failure = False
close_on_python_interpreter_crash=False
close_on_success = True
# -------------------------------------------------

########### acts only if close_on_python_interpreter_crash == False
# i guess not do -X for close_on_python_interpreter_crash=True


# Option to restart main code ("python_code_name" setting) when python crashes (or python returns not 0 with "sys.exit(returned_number)") instead of starting the after python crash script ("after_python_crash_code_path" setting below). It will pass the argument "crashed" to python for the restarts (python can check for that with sys.argv[-1]=="crashed"))
restart_main_code_on_python_interpreter_crash = False
# -------------------------------------------------

# ==========================
# ==== logging settings ====
# ==========================

# -------------------------------------------------
log_path_rel_to_wdir = "..\\log.txt"  # wdir is influenced by "start_in_shortcut_folder" setting
# -------------------------------------------------
log_even_with_terminal = True
# -------------------------------------------------
print_timestamp_style = "%H:%M:%S\t"
# -------------------------------------------------
log_timestamp_style = "%H:%M:%S\t"
# -------------------------------------------------
log_file_date_append_style = "_%Y_%m_%d"
# -------------------------------------------------
append_log = False
# -------------------------------------------------

# ====================================
# ==== terminal (visual) settings ====
# ====================================

use_fancy_terminal = True

# --------------------------------------------------
# settings that apply if use_fancy_terminal = False:
# --------------------------------------------------

# Terminal colors (leave empty for windows default. Options:
# Background:
# 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,8=Gray,7=White,9=LightBlue
# Text:
# A=LightGreen,B=LightAqua,C=LightRed,,D=LightPurple,E=LightYellow,F=BrightWhite)
terminal_bg_color = "9"
terminal_text_color = "F"

# -------------------------------------------------
# settings that apply if use_fancy_terminal = True:
# -------------------------------------------------

terminal_needs_input = True
dark_mode: bool | None = True  # None = Windows dark setting
accent_color_hex: str | None = "#08306b"  # hex color. None = Windows accent color
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

# =================================================

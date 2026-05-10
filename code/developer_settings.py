# ============================
# ==== Important Settings ====
# ============================

# -------------------------------------------------
# Name of this program:
program_name = "PyApp-Template"
# -------------------------------------------------
# Python version ("x"/"x.y"/"x.y.z"). Finds latest matching(msi-install-available) Python version. "" -> latest:
python_version: str = "3.14"
# -------------------------------------------------
# Path to end-user settings file (None to disable). File type can be anything openable by vscode/editor:
user_settings_path: str | None = "settings.py"
# -------------------------------------------------
# Names of created shortcuts (None to disable). Accepts for example f"{program_name}":
windows_terminal_shortcut_name: str | None = f"{program_name}"
terminal_emulator_shortcut_name: str | None = f"{program_name} (Terminal Emulator)"
no_terminal_shortcut_name: str | None = f"{program_name} (no Terminal)"
open_settings_shortcut_name: str | None = f"{program_name} - Settings"
stop_running_shortcut_name: str | None = f"Stop {program_name}"
# -------------------------------------------------
# String added before prints/inputs. Accepts datetime.datetime.strftime usage: e.g. "%H:%M:%S | ". None to turn off:
print_prepend: str | None = "%H:%M:%S | "
input_prepend: str | None = "%H:%M:%S > "
log_print_prepend: str | None = "%H:%M:%S | "
log_input_prepend: str | None = "%H:%M:%S > "
# -------------------------------------------------
# Program exit behavior:
# success = sys.exit(0)/sys.exit()/file end.
# failure = sys.exit(not-a-zero) e.g. raised Exception.Exception.
# crash   = python interpreter crash (where even try/except fails).
close_on_success = True
close_on_failure = False
close_on_crash = False
send_Windows_notification_on_success = False
send_Windows_notification_on_failure = True
send_Windows_notification_on_crash = True
open_log_file_after_success = False
open_log_file_after_failure = False
open_log_file_after_crash = False
# False for off. True for default. String for rel. path to .wav in C:\Windows\Media:
play_sound_on_success: str | bool = False
play_sound_on_failure: str | bool = True
play_sound_on_crash: str | bool = True
# -------------------------------------------------
# Start script in scipt folder or folder of the starting shortcut. (affects log_path_rel_to_start_folder setting below):
start_in_shortcut_folder = False
# -------------------------------------------------
# Logging behavior:
enable_log_for_Windows_terminal_start = True
enable_log_for_terminal_emulator_start = True
enable_log_for_browser_start = True
enable_log_for_no_terminal_start = True
overwrite_log = True
# Accepts datetime.datetime.strftime usage: e.g. "log_%Y_%m_%d". Affected by start_in_shortcut_folder setting above. None to disable:
log_path_rel_to_start_folder: str | None = r"..\logs\log_%Y_%m_%d.txt"
# ------------------------------------------------

# =================================
# ==== Less Important Settings ====
# =================================

# -------------------------------------------------
# How to treat alredy running program instances:
prevent_launch_if_existing_instances_running = False
close_existing_instances_on_start = False
prompt_to_close_existing_instances = True
# -------------------------------------------------
# Decide if global default (any version) Python should be used instead of automatic localized download and installation of Python/packages:
use_global_python = False
# -------------------------------------------------
# Start launch windows minimized where supported:
start_minimized = False
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

# =========================================
# ==== Launcher Mode Specific Settings ====
# =========================================

# --------------------------
# ---- Windows Terminal ----
# --------------------------

# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,8=Gray,7=White,9=LightBlue:
terminal_bg_color: str | None = "9"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,,D=LightPurple,E=LightYellow,F=BrightWhite:
terminal_text_color: str | None = "F"

# ---------------------------
# ---- Terminal Emulator ----
# ---------------------------

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

# -----------------
# ---- Browser ----
# -----------------

# =========================================

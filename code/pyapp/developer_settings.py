"""Developer settings: the program's identity, Python and packages, logging, and what happens when it ends.

Start at IMPORTANT; most projects never need to go further.
Relative paths in this file are interpreted as relative to this file.

Settings marked [bootstrap] are also read by the Windows bootstrap before any Python
exists. Keep each of them on ONE line as a plain literal ("text", True, False):
no expressions, f-strings or line continuations.
"""

# IMPORTANT:
#   program identity, Python/packages, logging switches, and multiple instances.
# MEDIUM:
#   launch/window behavior, completion actions, taskbar/notifications, shortcuts and logs.
# LOW:
#   appearance, shortcut names, Python/uv installation and optional integrations.

# ========================================
# ==== IMPORTANT =========================
# ========================================

# --- Program ---
# Used for the shortcuts and window titles:
program_name = "PyApp-Template"

# --- Python and packages ---
# [bootstrap] Python version requested from uv:
#   ""        newest stable Python, chosen once and then kept (see dev tool "update-python")
#   "3.14"    any 3.14.x (uv picks the newest patch)
#   "3.14.6"  exactly that patch
#   "3.14t"   free-threaded build; any other uv request string such as "pypy@3.11" also works
#   "3.12-3.14", ">=3.12" or "3"   any version inside, a range in either order ("3.12-3.14.2" stops at 3.14.2);
#             like "", the Python chosen on the first start is kept while it is inside (see dev tool "update-python")
# Supported: every version uv can provide (Windows x64 currently 3.8.2 and newer).
# The launcher itself needs Python 3.8 or newer. Changing this later offers a migration menu.
python_version = "3.14"

# Packages the app needs, one per line between the triple quotes, like a requirements.txt: PyPI names with optional
# version limits such as numpy>=2 or pillow==11.*; # comments and --hash options are fine.
# Only strings are accepted; use "" for no packages.
# The launcher installs exactly these, with the versions recorded in pyapp/generated/uv.lock (commit that file).
# A package removed here stays installed until you run the dev tool "sync".
# The dev tools "add", "remove" and "find-imports" edit this for you.
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

# ========================================
# ==== MEDIUM ============================
# ========================================

# --- Starting and stopping ---
# The Python file the launcher runs. It must be inside the code folder, but not in code/pyapp.
# Imports start from its folder, like `python main.py`. Run Setup again after changing it (for the Edit Code shortcut).
# The code folder is also on the import path, after the main script's folder.
main_script_path = "..\\main.py"

# String arguments passed to main.py:
args_for_main_py = []

# Environment variables set for main.py, e.g. {"MY_SETTING": "1"}.
# PYTHON* variables have no effect on main.py itself, because it runs with -E.
environment_for_main_py = {}

# Working folder. True: keep the folder Windows starts the shortcut in; False: main script folder.
# Setup leaves "Start in" empty so it does not pin a moved shortcut to its old folder.
# Windows chooses the starting folder; True does not locate the .lnk file itself.
start_in_shortcut_position = False
# Explicit working folder for main.py: absolute, or relative to this developer_settings.py.
# "" keeps start_in_shortcut_position above. The folder must already exist; imports are unchanged.
working_directory = ""

# Stop shortcut and instance_policy "replace": seconds a running instance gets to close by itself
# (its windows receive a normal close request, a console app gets Ctrl+C) before it is terminated.
# 0 terminates immediately.
stop_timeout_seconds: float = 3

# Ctrl+C / SIGINT: "interrupt" (normal KeyboardInterrupt), "ignore", or "confirm" (Windows Yes/No dialog).
# Stop/replacing a run still interrupts or terminates it. Explicit raise KeyboardInterrupt and
# handlers installed by the app itself are not suppressed. This does not block Ctrl+Break or Task Manager.
keyboard_interrupt_action = "interrupt"

# Optional non-interactive cleanup script after a detected hard interpreter crash. "" disables it.
# Absolute, or relative to this file; runs once in a fresh managed Python with the app's working
# folder/environment. Its stdout/stderr go to a separate .recovery.log; normal crash reporting stays.
# May point to main.py to rerun it once. Receives args_for_main_py + launch arguments + a final "crashed".
# The recovery is noninteractive and unwrapped; its own crash is never recovered. An inherited
# marker also prevents recovery if it invokes the launcher. Use the launcher for a normal later run.
after_interpreter_crash_script = ""

# --- Terminal host ---
# True:  classic console (conhost.exe). No tabs, looks more like an app, but text rendering and zoom are worse.
# False: Windows Terminal (wt.exe). Tabs, better text rendering and zoom.
#        Falls back to the classic console with a warning if Windows Terminal is not installed.
use_classic_terminal = True
# The browser terminal shortcut (browser_terminal_shortcut_name) shows the console as a terminal in a new tab of your
# default browser instead, with the same input, Ctrl+C, colors and titles: sharp text, zoom with Ctrl+wheel or
# Ctrl+/-, clickable links, copy and paste like Windows Terminal. By default, closing the tab ends the program
# (see confirm_on_close). Needs Windows 10 1809 or newer.
# Its address stays the same, so it can be bookmarked (works while the program runs); Setup shows it.
#   ""  automatic: http://<program name>.localhost:<port of this project folder>/<key>/
#   e.g. "http://my-app.localhost:8765" or "http://127.0.0.1:8765" (the key is added; it is kept per PC
#   in pyapp/generated and never committed). Setup also registers the start link <program name>://start,
#   which starts the program in the browser terminal, e.g. from a bookmark.
browser_terminal_address = ""

# --- Startup ---
# Only for no-terminal starts: show a branded, animated splash during environment preparation and startup.
# No extra packages; skipped for minimized starts. Closes at app handoff, not GUI readiness.
# No-terminal starts show it for at least 0.5 s, in parallel with the app (no startup delay).
# Begins after the bootstrap has found Python; unavailable Tk is silently skipped.
show_splash_screen_for_no_terminal_start = True
# A line under the app name; each start shows the next one (in this order, repeating; remembered per PC
# in pyapp/generated). Too long lines are shortened with "...". Use [] for none.
splash_screen_messages = [
    "Built with PyApp-Template launcher",
]
# Start automatically when this Windows user signs in. Run Setup to apply or remove the Startup shortcut.
start_on_windows_start = False
# Which launcher to use at sign-in: "no_terminal", "terminal" (configured conhost/WT), or "browser".
windows_startup_launch_mode = "no_terminal"
# Start with the window minimized:
start_minimized = False
# Maximize the managed native terminal/browser window on start; takes precedence over start_minimized.
# This does not resize application-created GUI windows.
start_maximized = False

# While main.py runs, request protection against automatic idle sleep / display timeout.
# Both off: Windows power settings apply. Explicit Sleep, lid actions and policy still apply.
prevent_sleep = False
keep_display_awake = False
# Restore the classic console/browser terminal on the app's first print/error output (once).
# Hidden starts stay hidden; native Windows Terminal focus is unsupported. Windows may restrict focus.
foreground_on_first_print = False

# --- Terminal output ---
# Wrap long output lines (conhost and WT). False uses Windows native no-wrap mode:
# characters at the right edge may be overwritten; this does not add horizontal scrolling.
# Browser: default for its live Wrap lines switch; off uses horizontal scrolling up to
# 1,000 columns. The browser remembers a user override. Log files keep the full output.
wrap_terminal_output = True

# --- Native window controls ---
# Native terminal window (conhost and Windows Terminal); browser windows are left alone.
# Alpha affects the entire window, including text: 1 = opaque, 0.8 = 80% opaque; 0 < value <= 1.
# None preserves the host's default opacity.
terminal_alpha = None
# Keep the native terminal above other windows (does not repeatedly take keyboard focus).
always_on_top = False
# Classic conhost only; Windows may disable a single button rather than hide it.
# Windows Terminal draws its own caption buttons, so these do not apply there.
hide_minimize_button = False
hide_maximize_button = False
# Permit the corresponding system-menu commands and caption actions (classic conhost only):
allow_minimize = True
allow_maximize = True
# True: minimizing the native terminal hides it from the taskbar into the system tray near the clock.
# It keeps running. Click its tray icon (possibly under the hidden-icons arrow) to restore it;
# right-click for Restore / Stop program. Every minimize requests a Windows notification explaining this.
# Windows / Do not disturb may suppress the banner; the tray icon still restores the window.
# Works for conhost and a dedicated WT window, including start_minimized. Browser/GUI windows are untouched.
# allow_minimize=False still disables the normal conhost minimize action; hiding its button removes that route.
replace_minimize_with_minimize_to_system_tray = False
# Closing a terminal/tab while the program runs:
#   "close"   end the program as usual (all hosts)
#   "block"   disable the classic console's Close command (conhost only; Stop still works)
#   "prompt"  browser's leave-page confirmation (browser only; requires interaction with the page)
#   "hide"    close the browser tab but keep running; reopen its address to reconnect (browser only)
# Unsupported close modes fail before starting. Browser prompts also apply to reload/navigation;
# browsers may suppress them. Native console close notifications cannot cancel a close.
# This does not change close_after_* at program completion, Ctrl+C, Stop or Task Manager.
confirm_on_close = "close"

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

# Restore and bring the classic console/browser terminal forward when it stays open:
# These do not override close_after_*; native Windows Terminal focus is unsupported.
# Ctrl+C does not request foreground attention.
foreground_after_success = False
foreground_after_failure = True

# Open the normal log file:
open_log_file_after_success = False
open_log_file_after_failure = False
open_log_file_after_keyboard_interrupt = False

# Open the crash log (Ctrl+C does not count):
open_crash_log_after_failure = False

# Let the people using the app send you a crash: the crash window offers to copy the report
# (c), and to open a pre-filled issue form in the browser (i) when the address is set, e.g.
# "https://github.com/you/your-app/issues/new". Variable values are never included; paths and the
# error message are, so the user sees the text before sending it. "" for no issue form.
crash_report_copy_button = True
crash_report_issue_url = ""

# Play the default Windows sound:
play_sound_after_success = False
play_sound_after_failure = True

# Sound files; relative paths start at this file, %WINDIR% and other environment variables expand.
# "" means no sound. The play_sound_after_* switches above still choose when it plays.
sound_after_success = r"%WINDIR%\Media\notify.wav"
sound_after_failure = r"%WINDIR%\Media\Windows Critical Stop.wav"
# Completion titles are evaluated here; use f-strings to include program_name.
title_after_success = f"[Finished] {program_name}"
title_after_failure = f"[Failure] {program_name}"
title_after_keyboard_interrupt = f"[KeyboardInterrupt] {program_name}"

# --- Taskbar status (native conhost / dedicated Windows Terminal window) ---
# Show Windows' moving, indeterminate progress indicator while the program runs.
# This is activity, not a percentage; it is cleared/replaced when the app ends.
have_running_animation_in_taskbar = False


# A steady green (success) or red (failure) indicator, while the completion window stays open:
highlight_on_success = False
highlight_on_failure = False
# Request Windows' attention flashing until the window is activated; does not take focus:
flash_on_success = False
flash_on_failure = False

# --- Windows desktop notifications ---
# Independent of close_after_* and the browser's own switches.
# Requires Windows PowerShell and an enabled Start Menu start shortcut (run Setup after changing shortcuts).
# Windows notification settings / Do not disturb can suppress the banner. No extra notification sound.
# Clicking it opens the crash log (or the log); buttons open each. A new one replaces the previous one.
windows_notification_on_success = False
windows_notification_on_failure = False
# Use f-strings here for program_name. Only details known at exit are substituted later:
# {outcome}, {message}, {log_path}, {crash_log_path}. Other braces stay literal.
# The title and message are plain text; quotes, &, < and non-ASCII characters are safe.
windows_notification_title = f"{program_name}"
windows_notification_message_on_success = f"{program_name} finished successfully."
windows_notification_message_on_failure = "{message}"

# --- Settings file and shortcut locations ---
# File that the Settings shortcut opens, for the people using the app (any file type; "" to disable).
# This does not change Python imports or sys.path. Keep importable Python settings beside your app.
# Run Setup again after changing it:
user_settings_path = "..\\settings.py"

# The project folder always gets all enabled shortcuts. Setup removes earlier ones that are no longer wanted.
# Start Menu: a folder named after program_name with all enabled shortcuts:
start_menu_shortcuts = True
# Setup also creates matching .cmd entry points in root/batch_shortcuts (same enabled shortcuts).
# Start batches append their command-line arguments to args_for_main_py. No-terminal batches wait
# for startup acknowledgement; they can briefly show their calling console. Run Setup to apply.
generate_batch_shortcuts_for_args_launch = False
# Desktop: a list of "terminal", "no_terminal", "browser_terminal", "stop", "settings", "logs", "crash_logs", "open_code". Example: ["no_terminal"]
desktop_shortcuts = []

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

# --- Error reports ---
# Date format in crash reports:
error_date_format = "%Y-%m-%d %H:%M:%S"

# ========================================
# ==== LOW ===============================
# ========================================

# --- Terminal colors ---
# Background color: 0=Black,1=Blue,2=Green,3=Aqua,4=Red,5=Purple,6=Yellow,7=White,8=Gray,9=LightBlue. "" for default:
terminal_bg_color = "0"
# Text color: A=LightGreen,B=LightAqua,C=LightRed,D=LightPurple,E=LightYellow,F=BrightWhite. "" for default:
terminal_text_color = "F"

# --- Windows Terminal only (use_classic_terminal = False) ---
# Tab bar color, e.g. "#3B78FF". "" for Windows default.
tab_bar_color = "#3B78FF"

# --- Shortcut names ---
# Shortcut names. "" to disable.
terminal_shortcut_name = f"{program_name}"
no_terminal_shortcut_name = f"{program_name} (No-Terminal)"
browser_terminal_shortcut_name = f"{program_name} (Browser)"
open_settings_shortcut_name = f"{program_name} (Settings)"
stop_running_shortcut_name = f"{program_name} (STOP)"
open_log_folder_shortcut_name = f"{program_name} (Logs)"
open_crash_log_folder_shortcut_name = f"{program_name} (Crash-Logs)"
open_code_shortcut_name = f"{program_name} (Edit-Code)"

# --- Where uv and Python come from ---
# The dev tool "make-self-contained" sets these three to "local" and puts uv, Python and all packages into
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

# [bootstrap] uv download cache: "global" (uv's per-user cache, or your UV_CACHE_DIR if set) or "local" (code/pyapp/generated/uv-cache, grows over time):
uv_cache = "global"

# [bootstrap] Use Windows' certificate store for downloads (needed behind some company proxies):
use_system_certificates = False

# --- GitHub ---
# Tell you in Setup and the developer menu when a newer launcher (PyApp-Template release) exists.
# Asks GitHub at most once a day; never updates anything by itself. Off by default: it contacts GitHub.
check_for_launcher_updates = False
# GitHub Actions for this app; Setup creates or removes their files in .github/workflows:
#   "leaks"    on every push and PR to main: look for secrets and personal data
github_actions = []

# ========================================

# open this file if someone runs it directly (e.g. double-clicks it in Explorer) instead of running the launcher:
if __name__ == "__main__":
    import os
    import shutil
    import subprocess

    # VS Code if it is on PATH, otherwise Notepad. "code" is a .cmd file, so the command is one quoted string.
    editor = shutil.which("code") or "notepad.exe"
    subprocess.Popen(f'"{editor}" "{os.path.abspath(__file__)}"')

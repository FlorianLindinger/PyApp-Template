================
==== Future ====
================

Triaged 2026-11-11: repeats merged, typos fixed, done items removed (tests, ASCII banner, version
number, missing-package prompt, lint/test/hook tools, "what you can delete" docs, settings
validation, free-threaded Python, start minimized + foreground on first print, Ctrl+C settings,
traceback context lines, open log after failure). Items that refer to the old (pre-uv) launcher
are at the end under "Probably obsolete".


===================================
Launcher features
===================================

stuff like preventing x, asking for confirmation on x, or removing x.

can i set the venv for VS Code in the repo? (e.g. .vscode/settings.json -> code/pyapp/generated/.venv)

maybe i want support code that main.py can import (e.g. graceful shutdown, see future/graceful_shutdown). Ask AI for useful ideas.

long term: ways for the main script to talk to the launcher (and do stuff like the fancy terminal).
is there something useful i can pass in the globals of main_script? crashed variable? exit code of previous run? icon and name i guess

shortcuts that pass extra arguments: option to generate .lnk and/or .cmd for end users, where the .cmd allows adding args and passes them on. can the shortcut pass the remaining args? can at least the exe?

add setting to start main in a specific abs or rel folder (today only: script folder or shortcut folder).

add: restart_on_crash / restart_on_failure, with detection of an immediate fail again, max retries and max allowed in some time interval.
clarify what counts as a crash (interpreter crash vs. error in the script).

add setting: success_print = "[Program finished successfully]"
failure_print = f'[Program finished with failure] Program exited with code "{exit_code}"'
and explain that "" prints nothing.

setting how to deal with KeyboardInterrupt? (check what the keyboard_interrupt settings already cover)

maybe launch-mode dependent wait time before the "no launch" warning.

setting to stay open for exit code != 0?

setting to run in admin mode? does anything require admin?

add info print if settings don't make sense together.

update check: check for a template/launcher update on start (link, changelog), with options: don't check again / skip this version / show changes / install. setting for it; maybe only an info print with a link. maybe a shortcut for it.

add "enter y to open xyz".

prompt more fancy with prompt windows? confirmation question via Windows popup? fragile?

builtin profiling of the app? profiling of the launcher?

add a debug launch that starts in attached mode, and a debug launcher shortcut.

do i want timeout settings?

add confirmation to all folder removal? should delete_folder_safe return success / user refused / error?

does it accept and warn if the log is not accessible? make log.txt visible in the Windows preview somehow.

is sound playing + log opening + remain open on success somewhat slow?

do i even want a setting for faulthandler? test what faulthandler changes.

how is a PySide6 crash handled / caught?

use more input success/warn styles.


===================================
Windows integration (taskbar, notifications, tray)
===================================

Windows notifications: add setting "windows notification on <outcome> = 'Message'" (success/failure/crash).
- show under the program name and the correct app ID (also prevents spam)
- clickable notification
- warn if notifications are not allowed by Windows and mention where that setting is
- setting for a window prompt instead of the notification area?
- test notifications

flash in taskbar setting. what are all options for the taskbar appearance? colors and progress states (cycling, any % accent, yellow, red, none)? does taskbar highlighting have a color? highlight green on finished?

change title bar bg, text and border color on finish (green / red), also colors for the start settings. setting for title bar color and text color. is title color a better default than bg color?

re-enable the X button on finish?

system tray:
- prompt for minimize to tray (first time? setting)
- X button: option to prompt close / minimize to tray / cancel (could be annoying if assumed falsely)
- can i implement the tray as an intercepted command? replace the minimize button? avoid packages
- foreground should always unminimize and restore from tray
- make sure the tray remembers the position on overflow
- minimize via thumbnail buttons; also buttons for log, main script

jump list for right click on shortcut.

Stable window/layout profile IDs: save window position, opacity, shape, on-top state, etc. under a GUID.
Rule of thumb: use uuid.uuid5(...) when Windows should remember something across runs; use uuid.uuid4() when you want a new unique ID for this run only.

do i want to define the shape in conhost? via cols and lines, or a setting like a ratio?

check if i still need hwnd_candidates / get_candidate_hwnds()[0].

make a quick generate_shortcut.py that gets the app ID (and maybe the Python path) as a flag; bake in icon, minimized and so on; it should find the .py if not given and prefer main.py, main_script.py, start.py. write a line on how to change the app ID.

Windows Terminal: change the tab color for error or finish (green for success?); i can choose the tab title; also set a newly opened terminal to the warn appearance.

check if i still need the elaborate app ID setting or if a simple one works for both. check if setting the terminal app ID in a thread is actually faster. do i even need it if i stay in the original terminal?

test if taskbar grouping works for subprocess.Popen([python_exe, script_path], creationflags=subprocess.CREATE_NEW_CONSOLE).


===================================
Tracebacks and error output
===================================

clickable links in error reports: path:line to the failing line, and a link to open the main script (Windows Terminal; not possible in conhost?). open on the specific line with VS Code / Notepad++ / PyCharm; setting for which program.

change " Python child script traceback" text.

make the traceback use absolute paths, not ...\DONT_CHANGE\B\..\scripts\start_program.py.

how do i make long messages better in error reports? multiline?

make ===== as long as the message.

for conhost don't print extra lines for the download progress bar.

make install prints nicer; print the packages being installed.

handle a failing script wrapper self-run better.

wrap text in terminal prints as a setting.

make all prints homogeneous (ask AI, let it ask me which way i want).


===================================
Icons
===================================

make sub icons more visible; make the log icon darker for more differentiation; a folder sub icon for the folder shortcuts.

simplify icon generation; check HOW_TO_CHANGE_ICONS.txt.

make sub icons easier to change, outside the .py (in developer settings, not in DONT_CHANGE).

allow disabling sub icons by deleting them; print that one is missing.


===================================
Developer tools, compilation, repository
===================================

add batch to show installed packages and the diff to the defaults. show a dependency tree?

batch to compile (Nuitka): how to install Nuitka? auto icon. a python file for args and files for presets (AV safe, small, fast startup). compilation folder under dev_tools; a batch to clean it.
in compilation, have a script not meant to be changed with the defaults, copied over to the active compilation scripts? compilation script accessible to the developer (inside the dev folder).
make a batch that compiles main_script with its dependencies using the managed Python -> output with and without terminal. or something that converts the folder to a clickable app.
compile via GitHub Action as proof of exe content?
is there a way to make compiling faster when repeated?
do i need the unbuffered flag or other flags in the Nuitka compile? how to have faulthandler in compiled?

batch to get the Git folder size including all ignored files.

simplify the shortcut generation function into one function.

make a flowchart of the whole program: normal start, shortcut generation, ... (ask AI)

is there a way to optimize the project size for AI usage? or tell it to use the .gitignore?

check speed differences when using pymanager if available (probably not worth installing).

make startup faster: more lazy imports (ask AI where useful).

ask AI if the logging package is useful here. google drawbacks of -u.

check the tools scripts and their prints. move helper functions below the code where needed?

can python somehow plot in the terminal?

ask AI: general improvements, robustness, speed, comments, docstrings, more fail checks and error prints, ideas for the whole thing.


===================================
Documentation
===================================

add more explanation text to the .gitignore files.

mention what the effective license allows and the difference to MIT; add the DONT_CHANGE license summary to the main license.

check whether exception handling is mentioned in the README.

add a terminal emulator image to the README (once it exists again).

explain the limits on PCs without Windows long-path support.


===================================
Terminal emulator (future, WIP)
===================================

call the emulator WIP and don't fix problems there yet.

add an open-log button; log to file as an option with a clickable link.

show input is not working; add a timestamp at the same time. how to deal with prints without \n?

it does not respect the setting on highlight and foreground? highlight only when needed not working -> fix is_active_window?

change the order and defaults of the buttons.

change the color of the taskbar app bar; easy options for the main background, main field and button colors.

add an always-on-top button; allow a minimize button.

add "Remember buttons" (restart with the last button settings); save button state, window position and size in a file and reload them; remember the last window state.

add a timestamps button setting.

disable the Windows buttons as a launch option.

add a "3 bars" symbol to the menu button?

add a bulb for running / stopped / done / failed.

does fallback_terminal_icon work for compiled?

add a wrap-text option.

the first menu click is slow.

prompt for closure of "terminal title".

add fading of prints as a launch setting.

how to add button settings? easy way to add buttons (e.g. a link-to-settings-file button: new button spawning if the name is not in the current ones).

google more ideas for a fancy stylesheet; add comments to the stylesheet; change all "none" in the default stylesheet.

reduce padding and optimize the style while respecting the Windows dark theme; some padding clips in the top right corner; 3D buttons that stick out when disabled and in when enabled; scalable text input; change the accent slightly for a shadow effect; down arrow of the menu overlaps the text; more hover text for "to tray".

make error prints bold; correct color formatting like tracebacks in VS Code; red background on error.

move the emulator part to compiled and run the rest as python via the runtime (drawback: no attached terminal mode, long target path).

return the errors of the python script and my own crashes (p.returncode).

a help button that asks the script?

enabled buttons don't change color on hover.

prompt window on crash:
 def _show_critical_error(self, title: str, message: str) -> None:
        msg = QMessageBox(None)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.Window)
        QApplication.alert(msg)
        msg.exec()

option for no extra buttons (no menu); make the top bar hide and only appear near the mouse, with a pin.

on crash go to the foreground and alert.

indicate which buttons toggle and which trigger.

add search; make terminal output searchable.

typewriter effect.

transparency button: prompt for alpha, maybe a slider (or under "Window").

make buttons and menu scrollable when too small.

minimize to tray: not hidden behind the up arrow (remember once set, maybe force it visible on start); slight animations; explain the tray more in the hint.

menu: unpinned first (at least on start, only refresh on open); center labels and save space horizontally.

ask AI if features of the old tkinter fancy terminal are missing; also look at its TODO.

auto clickable links and paths?

do progress bars work? maybe build one in.

option to change the taskbar icon color at runtime and before; tell the user how to change icon, name and color at runtime.

have tracebacks inside the Qt terminal too.

add always-foreground option. is cls implemented? can i process ANSI codes?

make terminal emulator input inverse bg and fg?

defaults:
    INPUT_PREPEND = ">>> "
    INPUT_PRINT_BG = "none"  # replaced later if the accent setting is set
    INPUT_PRINT_COLOR = "none"
    ERROR_PRINT_COLOR = "#FF5252"
    ERROR_PRINT_BG = "#FFFFFF"

replace the eval of text printed by the child (old terminal_emulator.py) with an explicit command protocol, e.g. JSON lines like {"command": "set_button_visible", "name": "stop", "value": false}.

use Nuitka attach mode to have 2 exe in one (also better for AV safety)?

how should the watchdog set the title for the fancy terminal and browser?

add an explanation for the PyQt6 license (if the emulator ships).


===================================
Browser terminal (future, WIP, see future/browser_terminal)
===================================

run the terminal in the browser; ask AI if there is an easy way to run it as a tab; start with a bookmark.

call it WIP and don't fix problems there yet.

is cls implemented?

add all buttons of the fancy terminal to the browser, maybe more.

Behavior	Current browser terminal	xterm.js + pywinpty
print() output	Works	Works
input()	Works line-by-line	Works like terminal
Arrow keys	Browser text box only	Sent to program
Ctrl+C	Not real Ctrl+C	Real terminal interrupt
ANSI colors	Printed as raw escape codes unless parsed	Rendered by xterm.js
Progress bars	Often messy	Usually correct
Interactive CLIs	Mostly bad	Good
sys.stdin.isatty()	Usually False	Usually terminal-like
Resize behavior	No real terminal resize	Can resize PTY cols/rows
Complexity	Low	Medium
Dependencies	None	pywinpty + bundled xterm.js


===================================
Unrelated (other repositories)
===================================

check what functions to copy to fun_flo in the terminal script.

add a venv to "python -> exe" (see the compiler folder); test --nofollow-import-to=*.tests for all; add docstrings to the "python to exe" scripts; create a license template for the exe compiler folder (also check for a template); in the python compilation batches, make the input a txt file for additional Nuitka args.

VS Code Ruff log:
2025-11-12 14:51:26.911650000  INFO Registering workspace: c:\Users\user\Documents\Repositories
2025-11-12 14:51:26.978416400  INFO Configuration file watcher successfully registered
2025-11-12 14:51:27.024018800  INFO Server shut down
[Error - 2:51:27 PM] Server process exited with code 0.
2025-11-12 14:51:27.215409000  INFO Registering workspace: c:\Users\user\Documents\Repositories
2025-11-12 14:51:27.216785600  INFO Configuration file watcher successfully registered
2025-11-12 15:11:42.427337600 ERROR Failed to load settings from `configuration`: error looking key 'env:USERPROFILE' up: environment variable not found
2025-11-12 15:11:42.427384900  WARN No settings available for file:///c%3A/Users/agpup/AppData/Local/Programs/Python/Python313/Lib/ctypes/__init__.py - falling back to default settings

can i make interactive turn into non-interactive on reopen?

make side groups in VS Code smaller for scrolling over, or add a maximize button.

combine stuff from PyBoson and the rest in the GUI folder in utilities.

move batches to some kind of folder in the utilities repo.


===================================
Probably obsolete (refers to the old pre-uv launcher; delete when confirmed)
===================================

old components that no longer exist: embedded python in DONT_CHANGE\P, python_packages, pipreqs, common_variables, py_env, portable python batches, compiled terminal_emulator\run.exe, script_after_interpreter_crash_path / after_python_crash_code, start_program terminal modes, ship_compiled_fancy_terminal_emulator / ship_backend_python_and_backend_packages, "future smooth" ASCII font.

- trim the python packages folder / python folder.
- don't double the error message for the no-internet Python version check; FULL_VER in the batch is " " without internet.
- convert the portable batch to python; fix portable creator batches not using the given paths; make robust against people deleting the python_environment parent folder; better print for a missing portable python.exe.
- update pip after the Python download or venv? add pip upgrade to the venv or disable the check.
- don't install default packages during venv setup (save_list_of_packages_needed_in_files -withVersion.py).
- install needed packages did not work for PyBoson.
- warning after git clone for the old VERSION.txt / readme.txt paths.
- support Python 3.6 (the launcher now needs 3.8+).
- make the embedded python more trusted so it does not prompt the first time.
- renaming python.exe (shortcuts and batches have the python name hardcoded); passing the name/icon to PySide via a renamed python.exe.
- Finish crash handling parity between script_wrapper and the terminal emulator; unify wrapper and emulator behavior (logging, timestamps, close-on-*, PID handling, faulthandler).
- the terminal_emulator e.code = 0 / '%H:%M:%S\t' OSError for an outdated compiled terminal.
- re-add the browser shortcut: start_browser_shortcut_name = f"{program_name} (Browser)".
- move set_terminal_colors / setup_unminimize_and_foreground_on_first_print to main; move stuff to the watchdog so the visible terminal disappears fastest; "make start: This script is intended to be launched in a visible terminal that is minimized on start".
- do i need to make terminal_args safe?
- old settings: prevent_launch_if_existing_instances_running / close_existing_instances_on_start / prompt_to_close_existing_instances (now instance_policy).
- move over arg_to_str / arg_to_bool.
- shortcut generation requiring admin; notepad.exe for dev_tools requiring confirmation.
- mention that one can delete the compiled folder and pipreqs folder / P / packages / py_env; a tool to make the folder smallest; not shipping the terminal emulator (gitignore sync).
- do i want a "don't close any terminal" flag for start_program?
- sort common variables; remove function overkill in common code; paths without \\ at the end in common_variables.
- old README terminal-emulator TODO.

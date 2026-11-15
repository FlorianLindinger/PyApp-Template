# TODO

## 1. Release validation and publishing

- Test on Windows: Setup, start twice (second start fast), Stop on the example window (closes
  by itself), Logs/Settings/Edit main.py shortcuts, `status.cmd`, `change_python`,
  `make_self_contained`, a failing `main.py` (black window, traceback, "(no Terminal)" grouping).
- Run `DONT_CHANGE/tests/run_launcher_tests.cmd` on Windows (`test_windows.py` and the batch/Stop paths
  are skipped elsewhere) and `pyapp_tools/verify_launcher.bat`.
- Test a fresh download / new app creation / first use by someone else, and a moved and a
  copied project folder.
- Test new browser-terminal buttons: labels, icons.
- Spell-check READMEs, comments and messages.
- Tag the release on GitHub, update the repository topics/description, then keep developing on
  a dev branch (main only for releases and quick fixes).
- ask what all i have to test and do before release 1.0.0

## 2. Reliability and safety reviews (older reports; verify current behavior)

```text
check all repos for leaks

is portable installs code gitignored correctly

is something synced that is in gitignore?

do full install venv and delete venv test in all python version. kind of benchmark without adding global paths.

make it somehow safer for aborted installation of stuff. maybe folder deletion and end file signal creation

when python install fails how does it indicate? maybe just create something in end to show success?? not working at the moment. maybe really create a successful Python installation file that gets removed with delete_distro -> yes
might as well do success install indicator in python file in case someone delete all entries for better check then. maybe also still check for python.exe additionally

when it sees that 3.4 does not exist online. it has already delete the last. Only delete indicator and dist at last point

the python version indicated by the python file did not update for failed reinstall from m3.6 to 3.5. but py_dist was 3.5 . So either update even for failed or removed the old indication when i delete old? and make it possible for no python version indicator file

never close on backend failure: should be already? ask AI if could happen. THat should not happen. always open a new terminal to report. I guess no log then.

does it not stay open for start failure? is it most batch safe for any mistake in python scripts?

test if really portable for all local installs if no internet

Check that multiprocessing works in main.py under the wrapper, which is a common thing app authors will try.
```

## 3. Settings, hooks and tool reviews

review dev settings

think of hooks and workflow
git hooks: validate dev settings ....
where to put: DONT_CHANGE\pyapp_tools\src\git_hooks
ask AI what hooks/workflows i should offer to dev and git tools and so on. .... Should i move dev tools to subfolders?
add validate_dev_settings for app as tool and as workflow
ask for more workflows and actions
add pre commit hooks for example for just warning for leaks and asking for confirmation or something
do i want some tool of the git tools in dev helper? or github actions?
should i spawn the GitHub workflows only when activated and or detecting template repo so it does not spam root folder unnecessarily
can i review all git hooks and github workflows

ask ai what it would simplify or remove

manually look at all tools and see if need improvements

## 4. Documentation

readme:
it puts icon on opened terminal automatically. i guess one cant do normally if one want terminal to stay open on crash? bc shortcut to cmd? right?
background invisible app with log and crash log and stop button
auto good icon creation
combination with starter in taskbar auto for gui code

- Screenshots/GIF: shortcut icons, terminal appearance, taskbar grouping, colored traceback.
- Feature list: "fully reviewable code, no black box"; uv (shared cache, portable mode).
- Explain how main.py can use the launcher's environment variables (PROGRAM_NAME, ICON_PATH,
  LOG_PATH, APP_ID, PROGRAM_HAS_TERMINAL, ...), with small Tkinter / Qt examples.

add more explanation text to the .gitignore files.

check whether exception handling is mentioned in the README.

explain the limits on PCs without Windows long-path support.

## 5. Developer tools, compilation and performance

Show a diff to the defaults and a dependency tree in the package-list tool.

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

## 6. Launcher features

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

## 7. Error reporting and terminal output

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

## 8. Windows integration

system tray would still be nice but how to trigger? do i replace the x button. i guess generally the button features

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

## 9. Icons

make sub icons more visible; make the log icon darker for more differentiation; a folder sub icon for the folder shortcuts.

simplify icon generation; check HOW_TO_CHANGE_ICONS.txt.

make sub icons easier to change, outside the .py (in developer settings, not in DONT_CHANGE).

allow disabling sub icons by deleting them; print that one is missing.

## 10. Browser terminal

any more feature ideas for browser terminal?
reorder button
foreground on finish?

remaining buttons of the fancy terminal worth porting: confirm on close, timestamps on/off, a help panel with the shortcuts.

## 11. Other optional ideas

- Measure the start-up overhead against running "python main.py" directly
  (Dev Helpers `tools/measure_startup_time.bat`) and mention it in the README.
- Optional `.vscode/settings.json` generated by Setup (interpreter = `code/backend/.venv`,
  search.exclude for .venv/uv-cache), without overriding the developer's global settings.
- Setting to always open a terminal for the app.
- Hide the .gitkeep files in the logs folders.
- Traceback options: open the failing line in the editor, collapse library frames, copy to
  the clipboard, show local variables, clickable paths in Windows Terminal (OSC 8).
- make it work on linux in a minimal way
maybe Linux support without tools and no shortcut generation within root or something. Whatever best support would be for starting shortcut. no idea. minimal way to work i gues
test linux ask AI what parts

## 12. Other terminal-emulator ideas (future / unverified)

```text
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
```

## 13. Older notes to verify

```text

readme mentions:
mentuion in readme workflows and tools,auto package mapping for missong imports,...
remove maxi from screenshots and all data? ask AI if anything leaks?
comparison image: launcher batch,terminal,tkinter base icon and name with just my app on taskbar
why no compilation: cant inspect and modify code and AV trigger and slow start and hard to git share license and ... ask AI, transfer large file,  slow first run if compile at user end,...
No need for terminal for debug runs,.
easy close of bg only apps
LOG and crash log automatically
chick installation with uv compared to classic pip installation
no python ior uv installation needed and easily gast python version switch
robust again global python changes since auto installation and local venv
easily made portable
plug and play licensing and gitignore rules
low space launcher
Python version supported
better traceback that cut out wrapper code of this launcher
implemented settings.py file with shortcut to it
portable folder (including local venv and all)
automatic shortcut creation with possibility to generate also on desktop and start menu including automatic icon
easy good icon creation from png image include sub variants for different shortcut options.
auto name and icon change on failure and success (for terminal interface)
ready global variables for custom GUI scripts where they find path and app name  ...
made as compatible as possible with restrictive company controlled Windows settings
deliberately short names of backend to avoid problems with Windows legacy path length limitation when repository is placed very deep

add many comments to many points in the code that someone not experienced in batch and python fully understand whats happening where





Duplicated boilerplate. The same 10-line startup block is copy-pasted into 9 files. The Windows COM/GUID/error-code helpers exist twice (generate_shortcuts and console_tools).
Whole modules inside one try:. script_wrapper.py and process_exit.py wrap the entire module, which hurts readability and linting. A small if __name__ guard around main() does the same job.
Settings read once at import time. launcher_ui, open_* and gen_icons import values from developer_settings when they load, so they keep stale values after edit_settings and fail on import if the settings are broken.
Inconsistent setting names: enable_log_for_Windows_terminal_start, close_after_KeyboardInterrupt, keyboardInterrupt_sub_icon_scale. The 18 icon settings would be cleaner as one dict.
Uppercase DONT_CHANGE as a package name and OPEN_HOW_TO_CHANGE_ICONS.txt.cmd (a double extension that looks suspicious to users).

ask AI if it would rename files or folders

maybe reorder stuff in DONT_CHANGE

what is "scripts" even

remove useless settings and check all

remove most useless dev settings. hm i guess lest important is good enough

rename sub icon to overlay icon everywhere

in common code see if functions still need params

# how much of window removal of traceback should wrapper handle? can i make minimal? and want? simplify that in wrapper

use get_print_divider but make more efficient to not use shutil. i guess make it a length in common code or something

make color choices and so on for on finish. also maybe sort them by finish type

ask ai: is anything in common_code slow that should be other script or lazy import?

reorder main in watchdog

double check that everything in both common_code thing are common. maybe change for frontend into something like process args and common code

generally simplify whole path for normal start and once start that user would see.

check if something in common code and common_lauincher code is actually not common

ask for more ideas and improvements

make dev settings shorter

can or do i even want to change the icon/nam,e of a Tkinter or qt guis?

does "start_minimized = False" work and useful?

should i stop cache creation for backend tools? or all tools? bc path length safety

ask it if i should add test for app as option to add in maybe same as actions? how do people change it. will it override it later? mention if people can modify them

should i give them a structure for GitHub actions ready and manual?
understand first self. maybe already give them ability to check ruff and pyrefly? kind of future possibility

remove overweitre thing i guess

user tools: check for git leaks, run tests (stuff put in tests folder i guess), ...

File
What it records
.txt
Python prints, errors, and user inputs, with configured formatting and timestamps.
.output.log
Output captured outside the Python process, including native libraries and subprocesses that inherit stdout/stderr.
For ordinary print() calls, both contain essentially the same output. The difference matters when a native library or subprocess writes directly to the console: that can appear only in .output.log. Conversely, typed user input is explicitly recorded by the wrapper in .txt; raw output capture doesn’t reliably record it.
You probably don’t need both. For simplification, I’d keep one externally captured log for broad coverage, adding explicit input logging only if you need a record of user responses.

how to make it more checkable for user? not needed. who cares

i guess only leave one font option in. maybe just recreate with AI and see if different or better and more letter support especially umlaut

"""
 ERROR  "main.py" has a syntax error (details below).
============================================= main.py =============================================
Script: C:\Users\user\Documents\Repositories\PyApp Template\code\main.py
Error date: 2026-11-06 14:55:44
Python: 3.14.9

File "C:\Users\user\Documents\Repositories\PyApp Template\code\main.py", line 11
    root.title(os.env iron.get("PROGRAM_NAME", "Example GUI"))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: invalid syntax. Perhaps you forgot a comma?
===================================================================================================
Press Enter to close this window.
"""
DEFAULT IS:
"""
  File "C:\Users\user\Documents\Repositories\PyApp Template\code\main.py", line 11
    root.title(os.env iron.get("PROGRAM_NAME", "Example GUI"))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: invalid syntax. Perhaps you forgot a comma?
"""

make "Stop PyApp-Template" and all have black standard background by default and only switch to color once actual app starts bec bad contrast on some color

what do i really want. should code be only for end user and backend only for dev and dont_CHANGE only for me. But with uv lock and .venv and stuff then end user has more than needed. any workaround?

check dev tools and ask for more ideas

do i want DONT_CHANGEtmpdiagnostics.log in backend?

it should add tests and startup time and so on

think if i want:"4. Start the app with the generated shortcut. Edit `code/main.py`; add packages with
   `code/backend/dev_tools/add_packages.cmd` (or `uv add NAME` in `code/`).
5. Commit `code/pyproject.toml`, `code/uv.lock` and `code/.python-version` with your app;
   they are created on the first run and describe the exact environment.
"

.vscode/settings.json pointing at code/backend/.venv, since VS Code won’t find a nested venv on its own.

More useful crash reports: record the exact error time (now it’s the time the report is drawn), Windows version, the uv.lock hash or package list, and recognise more crash codes (0xC0000374 heap corruption, 0xC0000135 missing DLL, divide-by-zero).

consider: Process ID folder in your code folder. _CURRENTLY_RUNNING_.pid(.d) lives in code/, next to the user’s own code; it belongs in DONT_CHANGE\tmp.

why so long patj on  C:\Users\user\Documents\Repositories\PyApp Template\code\backend\DONT_CHANGE\temporary\runs\d4fc9fd96f064c3492764573d2326375\bootstrap.log

why need tmp/runs?

i can move pycache i guess. ask if worth it

what happens with venv when i move folder and global python no longer there?

why slow start?  make test

why are log hashes not same length

make tool smart enough for path length detection that it would pretend that all .py have written their cache

is it useful to stop creation of pycache everywhere for single settings file? or somehow move somewhere else

"""
Your pyproject question: yes, you can do that. Moving .venv, uv.lock, .python-version and pyproject.toml into code\backend is easy, because uv just treats backend as the project folder. Two costs:
VS Code and PyCharm won’t find the environment by themselves any more. You’d select the interpreter once (or Setup could write .vscode settings).
uv add typed in code\ won’t find the project; it would have to be run in backend\. The dev tools would handle that.
To make developer settings the only thing people edit, my recommendation:
Add a setting like packages = ["requests", "numpy>=2"] to developer_settings.py.
pyproject.toml becomes a file the launcher generates from that list. Nobody edits it.
add_packages / remove_packages edit the list in the settings file.
Only uv.lock must still be committed, because it pins the exact versions. .python-version could become an internal file.
If someone runs uv add by hand, the launcher detects that the generated file was edited and offers to take the change into the settings.
Two other options I’d rule out:
Putting the dependencies in a comment block at the top of main.py (a format uv understands) puts them in main.py, not the settings.
Plain requirements files instead of pyproject.toml work too, but drop uv add / uv lock, for no real gain here.
"""

make stop shortcut text nicer

(the import-name mapping is derived from pipreqs, Apache-2.0)

does it still auto find and how does it know that it di already

do i want .python-version or where it is? same for uv.lock

does desktop_shortcuts work for disabled by name?

do i still need:traceback_extra_lines: int = 3
# Color tracebacks in the terminal (log files are always plain text):
traceback_colors = True

how to make clear to not change python version via pyproject? needed?

should i prompt to auto determine packages or open requirements folder instead of default on?

chekci f i like the shortcut installatioj behavior and removal and so on

does it work to install form github a package?

do i need to update my python_env_crator. do i want that to be fully uv forced or fully both compatibly . does it work both atm?

are icons bad? Ask AI for better version and check first what is best currently

should i clean temporary whenever done?

def program_has_terminal():
    -> no. maybe just reuse some logic in exit process?
    -> but also it already does that, right?

apply template to exit
apply template to watchdog
should i add a "program has terminal " to template? would only change for backend watchdog

make verification better prints in end

have backend_python_finish_installation_relative_path in backend_vatribles.py? kind of not helpful. i need to read out the settings somehow but at that point i can just have another script. maybe just minimal python script to get the setting and then launch it in batch folder?i guesss i can just leave how is.

still test the install embed ypython batch generic

make import error fancy:
Missing import: requests
Suggested package: requests
Python executable: C:\...\python.exe

do i also want a test.py standin? to run tests
for test main.py have it make a tkinter GUI
... think of more tests i guess

print in red that standin script is used but dont have that in standin script

do i want to remove stuff from pyproject. ask AI what is houd do with it

do i want to force pyrefly setting in pyprkct

have way to exclude folder/fioels for verify

careful with setting overwriting global vscode ones

# def get_print_divider(message: str, symbol="=") -> str:
#     """Return an equals-sign rule matching message width without wrapping."""
#     longest_message_line = max((len(line.expandtabs(4)) for line in message.splitlines()), default=0)
#     terminal_columns = shutil.get_terminal_size(fallback=(80, 20)).columns
#     max_rule_width = max(1, terminal_columns - 1)
#     rule_width = min(max(1, longest_message_line), max_rule_width)
#     return symbol * rule_width

it should be able to catch syntax errors in wrapper and give good suggestion for syntax error in watchdog -> features form Python 3.11+
it does not handle syntax error in wrapper? handle that somehow better
does it handly syntax errors in all script where it can? mention the scrioüpt that it does not handle it.
dont do success terminal for on close?  i guesss only if anything happens? what for soud=
is crash txt report everywhere?
add a success theme for rich traceback
mention rich customizability. add more
make option which terminal to prefer for traceback and add clickable features. mention somewhere. also as general drawback of conhost in temrinalc hoice
can i have rich traceback nicely scalable in hindsight in conhost? do i want not conhost for newly opened?
add full path to file somewhere in rich and normal traceback print
choose good RICH_TRACEBACK_COLOR_THEME
checl how it nows how to remove frames
checkl rich traceback tempalce color options
except SystemExit as e:
            if (
                (e.code is None)
                or (isinstance(e.code, bool) and e.code == False)
                or (isinstance(e.code, int) and e.code == 0)
            ):
                sys.exit(0)
            else:
                # catches: sys.exit(True), sys.exit("a string"),sys.exit(non-0-int)
                save_traceback(e, python_script_path, crash_log_temp_path)
                sys.exit(1)
-> undo my changes i guess to get rich traceback back but ask it to simplify






when can i ever get interpreter_crsah?. ask AI?-> i should just do subprocess.run in child script and interpret the exit code. but at that point i might as well use backend for wrapper again. but for fancy traceback passing i need an wrapper the does run_path. So i need 1 start terminal in visible for short time, 1 backend watcher, 1 frontend wrapper that runs in itself the main script. so 2 longterm running. actually subprocess.run can capture the stderr but thats only text that rich can color.
I can have the watcher print the traceback since it is in the same terminal i guess. that can also handle all the other stuff like icon and all that i dont want any wrapper to do if i can avoid.->script_wrapper_watcher.py
maybe have setting to capture interpreter crash or not via additional backend watcher. kind of not because needs two different wrapper then if one handles icons and stuff in frontend and one in backend. careful with capture output and large prints. maybe better in frontend?
I guess that also makes the signal file for correct start useless? but still helps against any bug in watcher. also for future proff it is better if wrapper is as small as possible i guess
i guess i still need start terminal to always show error for safety and cant continue that because i might have invisible terminal. also better to have clear terminal but could also cls.
kind of overkill but needed to handle interpreter crashes. i mean a normal terminal also handler interpreter crashes but invisible terminal would not spawn one: only advantage is for invisible terminal and color traceback and on_crash settings.
Do i really care about failure and crash distinction?nooo. but maybe depending on code differen msg for interp crsh
But how do i pass args to watchdog? do i handle everything in invisible watchdog and create a terminal if error print? but all args i will pass to the different modes should be done in start_program so other start modes dont have duplicate. I guess i can just pass through the args.
think about where i still need setup_terminal_colors()
setup_unminimize_and_foreground_on_first_print()
shouldne watchdog watch for every launch mode. so it should handle the splitting into the modes. but also it could also continue in that terminal and only launch invisible_watchdog if no-terminal mode.
but i guess conhost and wt are fixed if i stay in same terminal. cant i make shortcuts obey and generally for all start follow their appearance changes. maybe functioN set_appearance_wt/conhost
apparently finding out if conhost vs wt is not necessarily reliably ->pass via shortcut. it is reliable to tell if there is a terminal tho (maybe).


```


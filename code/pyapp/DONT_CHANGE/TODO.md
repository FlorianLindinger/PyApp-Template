# TODO

Reviewed 2026-11-15. Release checks and safety reviews come first, followed by tooling, documentation and optional features. Uncertain older notes and technical examples are retained.

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



dont sync spawned: requirements.txt
where to see current packages?

what files do i want to not sync? how about code/backend/packages/_USE dev_tools FOLDER (IN PARENT FOLDER) TO CHANGE PACKAGES. i want the notice to be there but i want folder deletion not to trigger git? -> ignore all contents in folder?

fix gitignore for version indicator of Python when change

ask if faster startup possible

fix frontend packages being tracked and remove form history

what does:# Delete per-run diagnostic folders (temporary/runs) older than this many days (None keeps them):
max_run_folder_age_days: int | None = None

there was an error in installing python frontend when folder not existing but it continued before i saw-

check FRONTEND_PACKAGES_ARE_INSTALLED_MARKER_PATH

make missing PYHTON_VERISON a indication of broken or unsuccessful python installation and ->recread or prompt or something

fix make_file_to_indicate_frontend_pckgs_installed

in finish_backend_installation. how to make folder deletion safe-> maybe mentioned hardcoded name there in common_variables -> just import safe delete function. also for clear_folder_contents.

should i sync current python version? what if i put that in python folder as indication that successfully created and not deleted->yes

add error message for error in developer settings import everywhere it imports. but still ruff. can be critical bec even in generate shortcuts

delete traceback json before start

change clear_folder_contents in finish_backend_osntallion into delete folder safe

test what happens from prompt of delete_folder_safe. is abort wanted or do i want repeated prompt or print path to folder and manual prompt and then recheck ....
check if folder size check and walks are fast enough

do i want user to give chance to delete folder themselves before raising error. Like reprint path and not deleted until deleted. but also they are prompted and they should not be able to do more. maybe check after prompt if success and reprompt otherwise -> yes

ask if all tests are good and up-to-date.

check pyrefly ruff settings for DONTCHANGE

try fresh download and new app creation and then new user usage
test if folder move work.
check traceback. i guess have test file with all error kinds on dev helper repo
 ask AI for test i guess of all exit modes;

check the verifiers

check all dev tools fully
think about lnk names in dev tools
have close_terminal in dev tools? i guess batches handle already?
do i have nice terminals for package installation -> add printed line for start

test global uv installed

check once the full flow

test all options in python version not matching case

check that only main script errors are rich shc that ugly errors are more obvious unexpected.. but do i want some to be rich that could happen with wrong user settings? maybe actually do rich wherever user settings are involved.

test that that error print also unminimizes

test logic for frontend python and package installation for missing folder

test option to start minimized in all modes
test play sounds and start time
does it set all terminals ot that icon eg also from different opened apps form framework???

check all files with pyrefly script

fix and test all dev tools

test all starters

check py version change works

test if all prompts are forward to log

test if still portable/downloadable

test all settings for all modes

fix all ruff/pyrefly suggestions

ask it to double chec ensuer_venv

run path check again after all code has been run and local installation of everything

what is the logic of error handling in all files for normal start
has terminal:
    start_program
    all tools
doestn have:
    backent_watchdog
might have:
    wrapper

how to do PROGRAM_HAS_TERMINAL in exception in watchdog

fix backend watchdog

it did not bring to front for start and fail in start_rpogram imports
it did not unminimize on backend installation run of normal shortcut

fix # WIP_ save_exception_as_json()

fix: # WIP: assume no terminal and make new window and print traceback

write crash logs txt for all not success ones

in outer most except in watchdog. still create a new terminal

fix shortcut to open logs? should i also have shortcut for crash folder. maybe it should always open the folder? and live check for both the settings and not the baked in folder

does it handle well if main.py not there?

does it make folder for crash log and log log in worst case?

fix KeyboardInterrupt being slow to rich traceback. are alls slow?

it failed to not install packages after i choose that in wrong python version thing. Also it should roitn what dont get installed
there: "Reset packages" -> remove packages

failed start of main does not go to front on print

it does not handle keyboard interrupt?

log the rich traceback error still to file i guess unless it already is

fix that is not moving to foreground for first print

press enter to exit does not exit dev tools. add prints that file was save and where and clickable

does the settings.py import even work for non same wdir? mention? does it work for all modes?

fix wrapper
simplify wrapper.
why is failure of runpy so slow after traceback print in wrapper
why does my prints disappear in script wrapper beginning?
do i want to catch importError explicitly in wrapper? or otehrs launcerhs. -> i guess and then refer how to install to basically dev tools;
# somehow make parity. what if i remove the terminal in ´this version? might be even more work
do i want in wrapper and other to handle or not handle keyboard interrupt? probably i want. not atm
wait in wrapper how do i fancy print the tracebacks????
i guess cant claim in read,e
see if script wrapper could want lazy imports
installing rich traceback is slow? do i want it maybe only in wrapper? no error should usually occur in backend and when it occurs i deliberately do traceback
sort wrapper
should i use set_terminal_icon from wrapper or starter?
what if i either way need for app id stuff. can i make that simpler?
do i want a wrappercommon_code? wither way start and wrapper should be fast and no unnecessary imports
fix error print in wrapper mode having black kcolor for timestamp
dont i always handle a interpreter crash by wrapper and emulator? no need for setting?
in wrapper. do i want appearance change attempt for error?

fix needed for dev tools (ask ai if working somehow):
do i want python.bat and pip.bat in portable_python? only if i also add a terminal there i guess. for predictable behavior maybe outside in backend. or somehow buneled in portable Python? maybe different name and somehow easy name change at runtime
-> ship:
open_terminal_with_set_python_and_pip_target.bat

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

move readme resources to data in DONT_CHANGE

update readme. compare with old readme what i want

add images of rich traceback to readme. also taskbar grouping with arrow and circle
ask AI for readme improvements: gif ,screenshots, windows symbol, project structure, updating, licensing, mention to replace readme,status badges,Installation or Quick Start . Fix how to copy from github as template or not GitHub
add screenshot logic and folder. maybe gif to show taskbar grouping
add feature description: fully reviewable code. no black box
remove .vscode and add to gitignore
where can i indicate that backend runs on embeddable python and not full version. Maybe docstring on all files.
do i want traceback message above or below? probably below and combo with short form-> change (see above/below). also include in rich for coloring?
test rich traceback for all options where fail and also all types in main script
do i want:  main.py:6 in <module>

any more features missing in README->backend watchdog, rich
-> differentiate into mayor/minor features

add uv as feature in README and that it can use global cache

add comment to check for syntax error in watchdog at specific path if did not show up

rename readmes to README.txt?

add image of rich traceback to readme. add image of shortcut how it looks like a terminal next to the shortcut to that. compared to combined.

renamed: generate requirements to "generate list of ...". Add readme that explains what they do
think if all tool names appear nice

-> mention somewhere pass of env variables
add examples how to set and get? :in their guis with example for pyside6/5 qt tkinter..

ask long think AI for docstring improvements
detailed docstring for dev scripts
summarize in file >100 lines docstring what scripts do
add docstring to everything even files;
in staret_program docsating: """WIP: Add args and defaults""" and what it all does in the script
Same detail in wrapper

underline in readme better visible?
update git topics and order
Fix Release in git

check overall start time overhead compared to global python. I guess check with batch i have that measures execution time and just a script that exits immediately. maybe mention that overhead in README

in readme image circle what all is different. i guess the terminal title and icon and colors. the taskbar grouping and icon. and have comparison what it would look like wibtittu

Reorder features in readme. Also tags. And add description

update _README in DONT_CHANGE

update size in readme

ask it to add comment to code blocks

bump to version 1.0 afterwards

clean git after committing backend

stay in dev after release for development other than quick bug fix

ask AI which backend settings i should simplify

ask AI for more structure and naming improvements

do i even need wrapper and watchdog both if same python version on all?

reorder dev settings

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

# sort and group functions in all scripts

move to function: # close existing instances or block start if already running, if enabled

check if rich traceback is as nice as possible

should i reuse the function that save txt from payload for printing fallback

do i need
"origin": origin,
"script_path": excepted_script_path,
in save_traceback? I guess script path is fine

do i want:
    def get_terminal_name() -> str:
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetConsoleTitleW(buffer, len(buffer))
            return str(buffer.value)
        except Exception:
            return "Terminal"

do traceback from any sysexit. even 0 if not close. also keyboard and anything. should i just always do that? ->yes try for all modes. make sure it json gets created done also in success cases

make better message where to check syntax:
    ====================
    [Error] Backend code did not seem to launch properly
    --------------------
    Launch mode: conhost
    Error code (potentially meaningless): "0"
    ====================
    [Error] Press enter to exit

i dont want to create new terminal if dev settings say to close i guess? or is mini popup nice reminder of finish?->yes. i could start minimized and only foreground when not closing? -> also only change title/icon/colors/appid if it stays open

do i need:
# 2 = failure in wrapper -> handle (expecting info via json)
# 3 = failure in wrapper error handler (has "input(...)"" -> close here)
# (4 = failure in this script (see Exception of main() below))

check # 3 = failure in wrapper error handler (has "input(...)"" -> close here)

# WIP: i could handle failure in wrapper most basic? i could handle enexpected failure anywher most basic?

remove global PROGRAM_HAS_TERMINAL -> down below should never be reached -> always new terminal

ask AI if functions are not used commonly or are but are not in common

how do i do traceback and running stuff in same terminal.-> one function for both

check if i want improvements in crash log txt

remove env_var_to_signal_startup_time_measurement

is everything used in develper_settings?

am i checking for global uv and global uv cache. should i write somewhere what it does?

ask for more ideas for dev_tools so no replacement needed later

make better print for default run

for not found python exe make better print what folder to search for and where was last time. resolve path. it also does not go to foreground:
[Error] Backend Python not found:
"C:\Users\user\Documents\Repositories\PyApp Template\code\backend\DONT_CHANGE\B\..\backend_python\python.exe"
Drücken Sie eine beliebige Taste . . .

# make clear drawback of uv is if not installed globally file will be 70MB larger

is rich traceback good looking=?

check if more stuff from backgorund_watchdog should be in commmon_code

where do i choose error colors?

i randomly get sometimes: [Info] AppID update skipped for hwnd 0x0000000000B1089C: SetValue System.AppUserModel.ID for hwnd 0x0000000000B1089C failed with HRESULT 0x80070578: unknown error

in backend make the processing in main again as matter of principle and pass as arg

maybe shorter time wait for start before complaining

can i raise in watchdog and directly call the rich function for that?

disable icons for success and so on for now. dont generate

apply temrplate everywhere

ask AI if anything would requires folder creation in case not synced in git and so on

do i handle pipreqs fail gracefully

update pyproject for updated pyrefly

split readme into main features and additional features

do i want to print path to log folder somewhere or even shortcut to folder?

take care that i dont offer wrong stuff for use_global_python: print info that global used and global need to be installed and what global versions ....

ask AI if script is efficient

offer install terminal open for missing package

ask for settings ideas and feature ideas

most of the stuff i do could be just once on shortcut creation and then shortcut directly from installed Python to main_script.
-> unique stuff is taskbar combining bc need shortcut generator
-> interpreter crash watcher is improvements for no terminal case
-> easily portable/git-shareable: shortcut creation from not very easy bc shortcut to batch/.py does not pin and everyhing else needs specific target then which is not noob proof->manual would work well.
-> sum of quality of life like stoppers and terminal for installation
-> auto install of packages that are too large to share or not allowed
-> can handle low version without compromises on background stuff
- logging and prepends i could always do in main
- rich traceback could also be installed
- crash handling for no terminal could also be just handled in main
->>>>>> add to README

time to print exception seems slow

somehow fix: [Info] AppID update skipped for hwnd 0x00000000009600E0: SetValue System.AppUserModel.ID for hwnd 0x00000000009600E0 failed with HRESULT 0x80070578: unknown error

make warning for os.abort .... also fancy

ask AI for problems with delete folder safer
ask AI what features are actually better than would otherwise have with somewhat easy solutiomsask AI for optimizations
ask AI what i can do to make whole thing leaner and simpler
only have basic traceback for outer most exception. ask AI for all paths of error handlöing
ask ai about pyrpoejct settings. how much do i want to prescribe? do i want at all or just empty?
ask AI for more test ideas/featues. Ask for recommendations to test the main_scripts. test via compile? easy way for git actions.... similar stuff
ask AI if i can harmonize coding conventions al little more

# checkl if wdir = None is what is expected

i dont need fancy traceback for errors outside of main_script i guess but dev settings could cause crashes

set the batches to respect the terminal_mode and launch_mode

dont allow for empty app id?

i guess i still want stat_pgoram to start minimized and foreground on first print and also install there such that visible but not staying

what is the convention with _ infron to script. shouldnt wrapper and watchdog get also. or maybe just not the print rich traceback. but that either way will disappear now.

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

try popen after setting app id very early and maybe sleep before popen

can backend modify the terminal id for the frontend?

recheck logic in tools

harmonize launcher pys. including shortcut generator: see _script_template.py

for all the shortcuts: what do i want for appearance. does wt or conhost have better taskbar appearance: icon , name?
do i want to rename and icon ... for scripts that dont launch program?
conhost takes icon and title from shortcut. wt does not? but i can set title manually
conhost just better i guess-> wisscht
shortcuts have terminal preference
checkout terminal tab in shortcut properties

move batch creator function inside install python function

check and test python install
test how low versions go. hardcode error message for too low in start
check if pip install is overkill
chain pip upgrades in  until newest installed

for option 2: reinstall python and not packages: does it spawn the packages installer file?

spawn missing python version file for every get_python_version usage

earlier generate th note where to change packages. wasnt there after package fail

better error message for pyavkage version not existing in that python version

maybe make easier to reset versions of default packages for current version. does the option prompt. test the python version change prompt

what if i dont want to foreground on first print? because already foreground? shpould not matter since first print gets that out of the system immediately anyway

# more low tech to brinog to foregorund? on outer most exceptijn

might as well unminimize+foreground on bg=unexepcedt errors
do i generally want to bring to foreground as well for error? also change appearance?
but setup_terminal_colors_and_unminimize_on_print already does that anyway?

does all terminal appearance change work for multiple open? or normal terminal open?

review backend test tools at some point

have a template for the dev tools and backend test tools?

how do i give nice rich traceback in fails of main_script? launch in same terminal a backend python?
somehow pass the e
i cant just run another wrapper for rich traceback

ask AI to harmonize all fail print messages

st terminal appearance for shortcut generation. color but also icon and title?

setting to append number to log if existing

conhost cant do color ansi!!!! but i can enable in python

should i do ansi colors instead of fg bg color of terminal?

do i want all initial python start script and all dev tools and all to change terminal bg? via common function . including generator shortcut. also increase size for conhost launch

review  if close_already_running_instances_on_start or prevent_start_if_already_running:
in start_program

do i want to remove stale PID lines in start_rpgram? test how slow i guess

maybe just have print2? no that would not work for imported sub functions.
i need to know if started minimized and that not raised yet and then raise. i guess i could just raise once regardless if start minimized. but all script have defined if minimized so they know definite. i gues replacing prints and errors + global variable (test if works for subscript printing function) and raise once. local variable could be used to know if minimized. but then also variable in common_varialbes would do and pass to generate_shoerttus




```


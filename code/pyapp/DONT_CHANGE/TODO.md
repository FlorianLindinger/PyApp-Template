# TODO

add the windwos taskbar color thing and porgess and so on

minimize to tray and button replacement or disabling

always ontop opton wiht allow minizie if allwoed

hihglihgt settigns

windwos notifaction settings

confirm on close

terminal alpha?

can i make all temrinals soemhiow have lclikcable links

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

do i menation in readme htat otehjrwise combining wiht launcher woild have to pass ome kind of app id that has to be baked into the shrotcut and is not trivial to do
own icons for sucess and failure....
mention minimal linux comatilbity -> settings in linux file for python path?

add explanation to all codes that are not obvious and docstirngs

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

more test ideas?
3:51 AM
I’d prioritize these:
Silent crash while minimized: no earlier prints, then an exception. Verify foreground_after_failure restores the window.
Foreground settings matrix: first-print on/off × failure-focus on/off. Confirm each acts independently.
No unwanted focus: silent success, disabled settings, or an automatically closing terminal should leave your current window alone.
Minimized browser: verify restoration and selection of the correct terminal tab, with several runs open.
Missing-module recovery: traceback → export variables → cancel or install → restart. Ensure each action uses the correct run.
Export stress cases: recursive containers, huge arrays, broken __repr__, Unicode and an unwritable destination.
Moved project: paths containing spaces, Unicode and %; verify interpreter repair, logs, icons and shortcuts.
Cold offline start: test both an ordinary clone and a self-contained copy, with missing or broken Python.


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

link to fail line
Useful next additions, roughly by priority:
Clickable file-and-line links on every frame, opening directly in VS Code.
Relevant values beside each failing line, with the full variable list kept in the export.
Expandable library frames so your own code stays prominent.
Copy traceback and Open crash log buttons in the browser terminal.
Thread name and failure phase: startup, main code, worker thread, GUI callback or shutdown.
Comparison operators’ values, such as showing the actual array shapes when broadcasting fails.
One diagnostic ZIP containing the traceback, variable snapshot, output log and dependency versions.
Repeated-error grouping, showing a count instead of flooding the terminal.
test proi of traceback local variables

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

reorder button
foreground on finish?
timestamps on/off
browser: wrap text option as live button and deauflt
some kind of indicaor bulb if still running or done ? not sure waht colro code shoudl eb. or maybe just busy indicator with animator to indicate runnoing
make timestampos tolgglealbe? kind of problmatic to sync withj input unless i have it all running in browser logic
is it open log or open log folder. i guess i can have both. 
is it setting what buttons appear?
ask AI: any more feature ideas for browser terminal?


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

File
What it records
.txt
Python prints, errors, and user inputs, with configured formatting and timestamps.
.output.log
Output captured outside the Python process, including native libraries and subprocesses that inherit stdout/stderr.
For ordinary print() calls, both contain essentially the same output. The difference matters when a native library or subprocess writes directly to the console: that can appear only in .output.log. Conversely, typed user input is explicitly recorded by the wrapper in .txt; raw output capture doesn’t reliably record it.
You probably don’t need both. For simplification, I’d keep one externally captured log for broad coverage, adding explicit input logging only if you need a record of user responses.

More useful crash reports: record the exact error time (now it’s the time the report is drawn), Windows version, the uv.lock hash or package list, and recognise more crash codes (0xC0000374 heap corruption, 0xC0000135 missing DLL, divide-by-zero).


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


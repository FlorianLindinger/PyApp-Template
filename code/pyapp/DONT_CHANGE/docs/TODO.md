# TODO

improve Windows notification on tray text

are windows notification on x implemented? test them

Opus: add many comments to many points in the code that someone not experienced in batch and Python fully understand what's happening where

review dev settings

- re-enable the X button on finish?

- can I set the venv for VS Code in the repo? (e.g. .vscode/settings.json -> code/pyapp/generated/.venv)
- shortcuts that pass extra arguments: option to generate .lnk and/or .cmd for end users, where the .cmd allows adding args and passes them on. can the shortcut pass the remaining args? 
- add: restart_on_crash / restart_on_failure, with detection of an immediate fail again, max retries and max allowed in some time interval.

browser:
- are all settings in developer_settings implemented as much as possible?
- reorder button
- live print input prepend on/off: make timestamps toggleable? kind of problematic to sync with input unless I have it all running in browser logic
- is it open log or open log folder. I guess I can have both. 
- wrap text option as live button and default
- some kind of indicator bulb if still running or done ? not sure what color code should be. or maybe just busy indicator with animator to indicate running
- is it setting what buttons appear?
- ask AI: any more feature ideas for browser terminal?
- Resource monitor — display CPU, memory, and disk usage; optionally warn above thresholds. only if cheap or hidden by default

## 1. Release validation and publishing

- Test: Silent crash while minimized: no earlier prints, then an exception. Verify foreground_after_failure restores the window.
- Test on Windows: Setup, start twice (second start fast), Stop on the example window (closes
  by itself), Logs/Settings/Edit main.py shortcuts, `status.cmd`, `change_python`,
  `make_self_contained`, a failing `main.py` (black window, traceback, "(no Terminal)" grouping).
- Test a fresh download / new app creation / first use by someone else, and a moved and a
  copied project folder.
- Test dev settings appearance
- Test all browser-terminal buttons: labels, icons, button order, touchpad resizing
- Test all ways to crash a Python script/interpreter
- Test all dev and backend tools
- Test template to an app to see if problems
- Test on Linux
- Test all error handling paths. Build in errors to files.
- Test no-terminal error handling of custom GUI and no GUI
- Test if really portable for all local installs if no internet
- Test if log file is live print and viewable during run
- Test how is a PySide6 crash handled / caught?
- Test if it is safe for aborted installation of stuff
- Test that multiprocessing works in main.py under the wrapper, which is a common thing app authors will try.
- Ask AI if all launch options have the same features as much as possible
- Ask AI if I should change anything regarding git hooks and GitHub workflow for backend and dev or what I could add
- Ask AI what it would simplify or remove
- Ask AI what all I have to test and do before release 1.0.0
- Ask AI: general improvements, robustness, speed, comments, docstrings, more fail checks and error prints, ideas for the whole thing. find problems
- Run `DONT_CHANGE/tests/run_launcher_tests.cmd` on Windows (`test_windows.py` and the batch/Stop paths
  are skipped elsewhere) and `pyapp_tools/verify_launcher.bat`.
- Review all READMEs
- Tag the release on GitHub, update the repository topics/description (ask AI)
- Reset the CHANGELOG.md

## 2. Documentation & READMEs

README mentions:
mention in README workflows and tools,auto package mapping for missing imports,...
remove maxi from screenshots and all data? ask AI if anything leaks?
comparison image: launcher batch,terminal,tkinter base icon and name with just my app on taskbar
why no compilation: can't inspect and modify code and AV trigger and slow start and hard to git share license and ... ask AI, transfer large file,  slow first run if compile at user end,...
No need for terminal for debug runs,.
LOG and crash log automatically
quick installation with uv compared to classic pip installation
no Python or uv installation needed and easily fast Python version switch
robust against global Python changes since auto installation and local venv
plug and play licensing and gitignore rules
low space launcher
Python version supported
better traceback that cut out wrapper code of this launcher
implemented settings.py file with shortcut to it
portable folder (including local venv and all)
automatic shortcut creation with possibility to generate also on desktop and start menu including automatic icon
easy good icon creation from png image include sub variants for different shortcut options.
auto name and icon change on failure and success (for terminal interface)
made as compatible as possible with restrictive company controlled Windows settings
deliberately short names of backend to avoid problems with Windows legacy path length limitation when repository is placed very deep
it puts icon on opened terminal automatically. I guess one can't do normally if one want terminal to stay open on crash? bc shortcut to cmd? right?
background invisible app with log and crash log and stop button
combination with starter in taskbar auto for GUI code
do I mention in README that otherwise combining with launcher would have to pass some kind of app id that has to be baked into the shortcut and is not trivial to do
own icons for success and failure....
mention minimal Linux compatibility -> settings in Linux file for Python path?
Screenshots/GIF: shortcut icons, terminal appearance, taskbar grouping, colored traceback.
Feature list: "fully reviewable code, no black box"; uv (shared cache, portable mode).
Explain how main.py can use the launcher's environment variables (PROGRAM_NAME, ICON_PATH,
  LOG_PATH, APP_ID, PROGRAM_HAS_TERMINAL, ...), with small Tkinter / Qt examples.

Your pyproject question: yes, you can do that. Moving .venv, uv.lock, .python-version and pyproject.toml into code\backend is easy, because uv just treats backend as the project folder. Two costs:
VS Code and PyCharm won’t find the environment by themselves any more. You’d select the interpreter once (or Setup could write .vscode settings).
uv add typed in code\ won’t find the project; it would have to be run in backend\. The dev tools would handle that.
-> mention that people have to select?

Flowcharts?

## 3. Features

- can i have it easily run on linux by disabling all code parts for windows by kernel checking all. can it run if uv is installed global in linux. maybe make more compatible with linux and AI should ask what features it should do that are not easily implemented already. it should mention somewhere what all doesn't work on linux. Compilation settings. Compile for linux and mac? Can compile have problems with long paths? Batch to compile (Nuitka): how to install Nuitka? auto icon. a Python file for args and files for presets (AV safe, small, fast startup). compilation folder under dev_tools; a batch to clean it.
    - in compilation, have a script not meant to be changed with the defaults, copied over to the active compilation scripts? compilation script accessible to the developer (inside the dev folder).
    - make a batch that compiles main_script with its dependencies using the managed Python -> output with and without terminal. or something that converts the folder to a clickable app.
    - compile via GitHub Action as proof of exe content?
    - is there a way to make compiling faster when repeated?
    - do I need the unbuffered flag or other flags in the Nuitka compile? how to have faulthandler in compiled?
- can Python somehow plot in the terminal?
- File associations — open supported file types directly in the application. I guess I should not force VS Code. just start with default app for .py. or is that Python exe?? maybe have setting what it should be and mention.
- Graceful stop callback — let the app save data and release hardware before forced termination. Maybe I want support code that main.py can import (e.g. graceful shutdown, see future/graceful_shutdown). Ask AI for useful ideas.
- Automatic restart — restart after crashes with a delay, retry limit, and crash-loop protection. What is point actually? only helps for interpreter crash. maybe only do that then and mention
- Progress API — let application code report percentage, current operation, and estimated remaining time.
- Execution timeout — stop a stalled run after a configurable duration.
- git update check for final app: check for a template/launcher update on start (link, changelog), with options: don't check again / skip this version / show changes / install. setting for it; maybe only an info print with a link. maybe a shortcut for it.

## 4. Error reporting, terminal output & traceback

- Should I add package list to crash report? ... more
- clickable links in error reports: path:line to the failing line (per frame), and a link to open the main script (Windows Terminal; not possible in conhost?). open on the specific line with VS Code / Notepad++ / PyCharm; setting for which program.

## 5. Windows integration

- Windows also offers percentage progress, overlay badges, and thumbnail controls. Microsoft taskbar API
- all prints to Windows notification option?
- Actual progress percentage and status badges in the taskbar. Taskbar API. somehow integration with program
- is there other option for minimize to tray than replacing minimize button?
- Windows notification: show under the program name and the correct app ID (also prevents spam)
- Windows notification:clickable notification
- Windows notification: warn if notifications are not allowed by Windows and mention where that setting is
- can I modify what appears when I right click a shortcut?
- I can modify what appear when I hover over something in Windows taskbar when opened: add buttons?

## 6. Future


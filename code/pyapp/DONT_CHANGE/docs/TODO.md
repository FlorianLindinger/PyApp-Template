# TODO

improve windows notification on tray

add many comments to many points in the code that someone not experienced in batch and python fully understand whats happening where

make sub icons more visible; make the log icon darker for more differentiation; a folder sub icon for the folder shortcuts.

wrap text in terminal prints as a setting. can i change for wt and conhost? live setting for browser

## 1. Release validation and publishing

- Test: Silent crash while minimized: no earlier prints, then an exception. Verify foreground_after_failure restores the window.
- Test on Windows: Setup, start twice (second start fast), Stop on the example window (closes
  by itself), Logs/Settings/Edit main.py shortcuts, `status.cmd`, `change_python`,
  `make_self_contained`, a failing `main.py` (black window, traceback, "(no Terminal)" grouping).
- Test a fresh download / new app creation / first use by someone else, and a moved and a
  copied project folder.
- Test dev settings appearance
- Test all browser-terminal buttons: labels, icons, button order, touchpad resizing
- Test all ways to crash a python script/interpreter
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
- Ask AI if i should change anything regarding git hooks and github workflow for backend and dev or what i could add
- Ask AI what it would simplify or remove
- Ask AI what all i have to test and do before release 1.0.0
- Ask AI: general improvements, robustness, speed, comments, docstrings, more fail checks and error prints, ideas for the whole thing. find problems
- Run `DONT_CHANGE/tests/run_launcher_tests.cmd` on Windows (`test_windows.py` and the batch/Stop paths
  are skipped elsewhere) and `pyapp_tools/verify_launcher.bat`.
- Review all readmes
- Tag the release on GitHub, update the repository topics/description (ask AI)

## 2. Documentation & READMEs

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
it puts icon on opened terminal automatically. i guess one cant do normally if one want terminal to stay open on crash? bc shortcut to cmd? right?
background invisible app with log and crash log and stop button
auto good icon creation
combination with starter in taskbar auto for gui code
do i menation in readme htat otehjrwise combining wiht launcher woild have to pass ome kind of app id that has to be baked into the shrotcut and is not trivial to do
own icons for sucess and failure....
mention minimal linux comatilbity -> settings in linux file for python path?
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

- batch to compile (Nuitka): how to install Nuitka? auto icon. a python file for args and files for presets (AV safe, small, fast startup). compilation folder under dev_tools; a batch to clean it.
    - in compilation, have a script not meant to be changed with the defaults, copied over to the active compilation scripts? compilation script accessible to the developer (inside the dev folder).
    - make a batch that compiles main_script with its dependencies using the managed Python -> output with and without terminal. or something that converts the folder to a clickable app.
    - compile via GitHub Action as proof of exe content?
    - is there a way to make compiling faster when repeated?
    - do i need the unbuffered flag or other flags in the Nuitka compile? how to have faulthandler in compiled?
    - presets for compilation
- is startup as lazy as reasonable?
- ask AI if the logging package is useful here. google drawbacks of -u.
- can python somehow plot in the terminal?
- after interpreter crash backup python script launch
- File associations — open supported file types directly in the application. I fguess i should not force vscode. just satrt viwth default app for .py. or is that python exe?? maybe have setting what it shoudlk be and mention.
- Graceful stop callback — let the app save data and release hardware before forced termination. 
- Automatic restart — restart after crashes with a delay, retry limit, and crash-loop protection. What is point actually? only helps ofr interpreter crash. maybe only do that then and mention
- Progress API — let application code report percentage, current operation, and estimated remaining time.
- Execution timeout — stop a stalled run after a configurable duration.
- Start on windows start option
- can i set the venv for VS Code in the repo? (e.g. .vscode/settings.json -> code/pyapp/generated/.venv)
- maybe i want support code that main.py can import (e.g. graceful shutdown, see future/graceful_shutdown). Ask AI for useful ideas.
- is there something useful i can do with communication of main.py and the backend?
- shortcuts that pass extra arguments: option to generate .lnk and/or .cmd for end users, where the .cmd allows adding args and passes them on. can the shortcut pass the remaining args? 
- add setting to start main in a specific abs or rel folder (today only: script folder or shortcut folder).
- add: restart_on_crash / restart_on_failure, with detection of an immediate fail again, max retries and max allowed in some time interval.
- prevent keyboradinterrup option: with option how to handlöe
- update check for final app: check for a template/launcher update on start (link, changelog), with options: don't check again / skip this version / show changes / install. setting for it; maybe only an info print with a link. maybe a shortcut for it.

## 4. Error reporting, terminal output & traceback

- Should i recognise more crash codes (0xC0000374 heap corruption, 0xC0000135 missing DLL, divide-by-zero).
Should i add package list to crash report? ... more
- clickable links in error reports: path:line to the failing line (per frame), and a link to open the main script (Windows Terminal; not possible in conhost?). open on the specific line with VS Code / Notepad++ / PyCharm; setting for which program.

## 5. Windows integration

- Windows also offers percentage progress, overlay badges, and thumbnail controls. Microsoft taskbar API
- all prints to windows notification option?
- maximize on start option
- prevent sleep option. ask what default behavior is atm
also option to keep display awake
- Actual progress percentage and status badges in the taskbar. Taskbar API. somehow integration with program
- does it have option to hide x button?
- is there other option for minimize to tray than replacing minimize button?
- Windows notification: show under the program name and the correct app ID (also prevents spam)
- Windows notification:clickable notification
- Windows notification: warn if notifications are not allowed by Windows and mention where that setting is
- re-enable the X button on finish?
- can i modify what appears when i right click a shortcut?
- i can modify what appear when i hover over something in windows taskbar when opened: add buttons?
- system tray:does "stop program" option in system tray respect the close rules?
- system tray:foreground should always unminimize and restore from tray
- system tray:make sure the tray remembers the position 

## 6. Browser terminal

- reorder button
- are all settings in developer_settings implemented as much as possible?
- live print input prepend on/off: make timestampos tolgglealbe? kind of problmatic to sync withj input unless i have it all running in browser logic
- is it open log or open log folder. i guess i can have both. 
- wrap text option as live button and deauflt
- some kind of indicaor bulb if still running or done ? not sure waht colro code shoudl eb. or maybe just busy indicator with animator to indicate runnoing
- is it setting what buttons appear?
- ask AI: any more feature ideas for browser terminal?
- Resource monitor — display CPU, memory, and disk usage; optionally warn above thresholds. only if cheap or hidden by default

## 7. Future


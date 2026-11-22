# TODO

make the shortcut genraterotr and the icon generatero into generic file.
how can i keep generic ones spearate? is it worth it? what else should i make generic?

is generic a good name?

think abouti waht primpt option i want for crash: ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Crash log: <project folder>\crash logs\crash_log_<date>_<id>.txt
? Enter = close, v = save all traceback values and open them (not redacted), c = copy the report to send it to the developer:

-> press enter to open crash log

-> do i want windwos prompt on crash as option like a not that i have to ok? i guess as option

splash screen if cheap/free in tkinter

add raedme to fallbakc start

check api and main

- any more api ideas?

have comment for wrokspace vscode settings

move helpers to extra sectiopn ion api?

- improve Windows notification on tray text
- Windows notification when the window is closed with X: not implemented (the watchdog dies with
  the console). Idea: catch the close signal, start the notification as its own process within
  Windows' ~5 s, new "closed" outcome with its own setting.
- review dev settings (too long? move niche settings below an "Advanced" line, see REVIEW.md 1.3)
- Execution timeout — stop a stalled run after a configurable duration.
- update_launcher dev tool: download a release, show the CHANGELOG and new settings, swap DONT_CHANGE with a backup, run the checks; refuse major versions. (The update check itself exists: check_for_launcher_updates.)
- App update check for the people using an app: the app's own GitHub releases, e.g. app_update_repository = "you/your-app".
- File associations — open supported file types directly in the application. I guess I should not force VS Code. just start with default app for .py. or is that Python exe?? maybe have setting what it should be and mention.
- Should I add package list to crash report? ... more
- clickable links in error reports: path:line to the failing line (per frame), and a link to open the main script (Windows Terminal; not possible in conhost?). open on the specific line with VS Code / Notepad++ / PyCharm; setting for which program.
- all prints to Windows notification option?
- is there other option for minimize to tray than replacing minimize button?
- PyPy readiness check: on change-python to PyPy, test cheaply whether every locked package has a PyPy wheel (or is pure Python) and warn before switching.

What I'd cut from the README: most of "Common settings" (the paragraphs on taskbar, minimize-to-tray and notifications) into docs/RUNTIME_OPTIONS.md. Also the long "Building your app" paragraph about working folders, and the second traceback image. And I'd trim the comparison table to about 10 rows.

browser:
- reorder button
- is it open log or open log folder. I guess I can have both.
- ask AI: any more feature ideas for browser terminal?
- Resource monitor — display CPU, memory, and disk usage; optionally warn above thresholds. only if cheap or hidden by default

compilation:
- can i have it easily run on linux by disabling all code parts for windows by kernel checking all. can it run if uv is installed global in linux. maybe make more compatible with linux. Compile for mac? Can compile have problems with long paths?
- compile via GitHub Action as proof of exe content?
- is there a way to make compiling faster when repeated?
- do I need the unbuffered flag or other flags in the Nuitka compile? how to have faulthandler in compiled?
- look at my presets and test them (a real build of each preset; no behavior tests yet)

## 1. Release validation and publishing

- Test: Silent crash while minimized: no earlier prints, then an exception. Verify foreground_after_failure restores the window.
- Test on Windows: Setup, start twice (second start fast), Stop on the example window (closes
  by itself), Logs/Settings/Edit main.py shortcuts, the `status`, `change-python` and
  `make-self-contained` dev tools, a failing `main.py` (black window, traceback, "(no Terminal)" grouping).
- Click a Windows notification and its "Open log" / "Open crash log" buttons (only checked as XML Windows accepts).
- Test a fresh download / new app creation / first use by someone else (Windows Sandbox or a VM),
  a non-ASCII user name, a OneDrive-synced folder, and a moved and a copied project folder.
- Test dev settings appearance
- Test all browser-terminal buttons: labels, icons, button order, touchpad resizing
- Test all dev and backend tools
- Test template to an app to see if problems
- Test on Linux (WSL: run the test suite there, and "Start without launcher --LINUX.sh")
- Test all error handling paths. Build in errors to files.
- Test no-terminal error handling of custom GUI and no GUI
- Ask AI if I should change anything regarding git hooks and GitHub workflow for backend and dev or what I could add
- Ask AI: general improvements, robustness, speed, comments, docstrings, more fail checks and error prints, ideas for the whole thing. find problems. Feature ideas. Code style improvements. Implementation improvements. Speed improvements.
- Work through REVIEW.md (simplify/remove, before 1.0, README gaps, tests, launch modes).
- Run `DONT_CHANGE/tests/run_launcher_tests.cmd` on Windows (`test_windows.py` and the batch/Stop paths
  are skipped elsewhere) and `pyapp_tools/verify_launcher.bat`.
- Review all READMEs
- Fix the cut-off home folder path in the "Before" row of `taskbar-comparison.png`.
- Tag the release on GitHub (v1.0.0, semantic versioning), update the repository description and topics:
  python, windows, uv, launcher, python-launcher, desktop-app, template, project-template,
  shortcuts, crash-reporting, portable, tkinter, pyside6, no-compile, pyinstaller-alternative
- Reset the CHANGELOG.md

## 2. Documentation & READMEs

- README mentions:
mention in README workflows and tools, auto package mapping for missing imports,...
comparison image: launcher batch,terminal,tkinter base icon and name with just my app on taskbar
why no compilation: can't inspect and modify code and AV trigger and slow start and hard to git share license and ... ask AI, transfer large file,  slow first run if compile at user end,...
No need for terminal for debug runs,.
LOG and crash log automatically
quick installation with uv compared to classic pip installation
no Python or uv installation needed and easily fast Python version switch
robust against global Python changes since auto installation and local venv
plug and play licensing and gitignore rules
low space launcher
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
Screenshots/GIF: shortcut icons, terminal appearance, taskbar grouping, colored traceback.
Feature list: "fully reviewable code, no black box"; uv (shared cache, portable mode).

- Flowcharts?

## 3. Features

- Graceful stop callback — let the app save data and release hardware before forced termination.
  Part of a helper module main.py can import (stdlib only, no-ops without the launcher): notify(),
  on_stop(), set_progress(), message boxes, keep_awake(), report_error(), restart().
- Windows also offers percentage progress, overlay badges, and thumbnail controls. Microsoft taskbar API. Progress API — let application code report percentage, current operation, and estimated remaining time. Actual progress percentage and status badges in the taskbar. Taskbar API. somehow integration with program
- can I modify what appears when I right click a shortcut? (not for .lnk files without a shell extension)
- I can modify what appear when I hover over something in Windows taskbar when opened: add buttons? (possible via COM for the console window; high effort)

## 4. Future

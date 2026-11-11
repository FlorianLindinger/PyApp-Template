# PyApp-Template launcher (`DONT_CHANGE`)

This folder turns `code/main.py` into a Windows app: shortcuts with their own icon and taskbar
group, a Python and packages that set themselves up, logs, crash reports, a Stop shortcut and
developer tools. Application authors normally edit only `code/main.py`, `code/settings.py`
and `code/pyapp/developer_settings.py`; everything here is the machinery behind them and is
replaced as a whole when the template is updated.

This document explains how it works, file by file, for anyone who wants to understand, review
or change it.

- [Overview](#overview)
- [Design rules](#design-rules)
- [What happens when you start the app](#what-happens-when-you-start-the-app)
- [The other shortcuts](#the-other-shortcuts)
- [The Python environment](#the-python-environment)
- [Process control and Stop](#process-control-and-stop)
- [Errors, tracebacks and completion](#errors-tracebacks-and-completion)
- [Console output](#console-output)
- [Every file](#every-file)
- [Versions](#versions)
- [Tests, linting and type checking](#tests-linting-and-type-checking)
- [Licensing](#licensing)

## Overview

```text
 shortcut (.lnk)
   └─ B\W.bat / B\N.bat                       tiny batch file, the shortcut's target
        └─ bootstrap\run.bat
             ├─ bootstrap\ensure_runtime.bat   finds uv and a Python (cached in tmp\runtime.cmd)
             │    └─ bootstrap\resolve_runtime.py   only when the cache is stale: installs uv/Python
             └─ python -I -S scripts\entrypoint.py actions\start_program.py
                  ├─ scripts\env\venv.py: ensure_environment()   pyapp\generated\.venv matches uv.lock
                  └─ runtime\bg_watchdog.py   (new console, or hidden)
                       ├─ runtime\script_wrapper.py  ──runs──▶ code\main.py   (app's .venv Python)
                       └─ runtime\process_exit.py    success / failure / crash / Ctrl+C handling
```

Three Pythons can be involved, but usually they are the same installation:

| Name | What it is | Runs |
| --- | --- | --- |
| launcher Python | The project's Python, started with `-I -S`: isolated, no `site`, standard library only | everything in this folder except the wrapper |
| app Python | `code/pyapp/generated/.venv/Scripts/python.exe` | `script_wrapper.py` and `main.py` |
| uv's Python downloads | Python builds uv installs (per user, or inside the project with `python_source = "local"`) | the base of both of the above |

## Design rules

- **Standard library only, Python 3.8+.** Every `.py` file here runs on any Python uv can
  install, without packages: the app's packages can never break the launcher. Use
  `from __future__ import annotations` with `typing.List`, `Optional`, and `Union`
  so `typing.get_type_hints()` also works on 3.8 (Ruff preserves runtime typing).
  Use public protocols for structural types; no `match`, no parenthesized `with`, no
  `str.removeprefix`, no `functools.cache` (`tests/test_files.py` checks this).
- **Settings are read when needed, never at import time** (`config.settings()`), so a mistake
  in `developer_settings.py` becomes a short message with a line number instead of a traceback.
- **Every tool is a plain module with a `main()`**, run by `scripts/entrypoint.py`, which owns
  the error, exit-code and "Press Enter" policy (see [Errors](#errors-tracebacks-and-completion)).
- **Cosmetic steps never stop the app.** Window icon, title, colors, focus and taskbar identity
  may fail on some systems; those errors are recorded in `tmp/diagnostics.log`
  (`scripts/diagnostics.py`) instead of being shown or silently lost.
- **Nothing outside the project folder is changed** except what the settings ask for: uv's own
  per-user folders, the Start Menu/Desktop shortcuts and the per-user uv/Python install.
- **Paths are defined once** in `backend_settings.py`. The batch and PowerShell files cannot
  import it and repeat a few folder names; change them together (and `code/pyapp/.gitignore`).

## What happens when you start the app

1. **Shortcut.** Setup creates `PyApp-Template.lnk` with target
   `cmd /d /c call "...\DONT_CHANGE\B\W.bat" <app id>` (classic console) and the AppUserModelID
   of this project copy. The `(no Terminal)` shortcut targets `B\N.bat`. Both start minimized.
2. **`B\W.bat` / `B\N.bat`** set `PYAPP_LAUNCH_MODE` (`terminal` / `no_terminal`) and
   `PYAPP_ENTRY_SCRIPT=actions\start_program.py`, then call `bootstrap\run.bat`.
3. **`bootstrap\run.bat`** calls `ensure_runtime.bat` and then runs
   `"%PYAPP_PYTHON%" -I -S -X utf8 scripts\entrypoint.py "%PYAPP_ENTRY_SCRIPT%" %*`.
4. **`bootstrap\ensure_runtime.bat`** creates `tmp\` if needed and loads `tmp\runtime.cmd`
   (the paths of uv and the launcher Python) when its stamp still matches: this folder's path
   (a copied project never uses the original's uv/Python), the time and size of
   `developer_settings.py` and the time/size of `pyapp\generated\.python-version`, and both executables
   exist. Otherwise it runs `resolve_runtime.py`. The cache is UTF-8 and read with code page
   65001 unless its first line is `rem ascii`, so non-ASCII project paths work.
5. **`bootstrap\resolve_runtime.py`** (only when the cache is stale) reads the `[bootstrap]`
   settings from `developer_settings.py` with a line parser (one-line literals; the last
   definition wins, like Python), finds or installs uv (`uv_prefer`, `uv_install_if_missing`,
   `uv_version`; a local uv is downloaded from GitHub and checked against its SHA-256), finds
   or installs the project's Python with uv (`pyapp\generated\.python-version`, else `python_version`),
   checks the 3.8 minimum and writes the cache. It holds `tmp\bootstrap.lock` so two starts
   do not install at the same time.
6. **`scripts\entrypoint.py`** puts the `code` folder on `sys.path` and runs
   `actions\start_program.py`'s `main()`.
7. **`actions\start_program.py`** validates the settings, resolves the launch mode (`conhost`,
   `wt` or `no_terminal`; Windows Terminal falls back to the classic console when missing),
   gives its own minimized window the app's title, icon and taskbar group, applies
   `instance_policy` (allow / focus the running one / ask / replace / block, see
   `scripts\instance_policy.py`), deletes old run folders when no instance is running, warns about outdated "open" shortcuts and
   calls `ensure_environment()` (see [The Python environment](#the-python-environment)).
   It then reserves a run folder `tmp\runs\<id>\` and starts the watchdog in a new console
   (`conhost.exe` or `wt.exe`) or hidden, and waits until the watchdog writes
   `startup.json` ("started", "cancelled" or an error). Then this window closes.
8. **`runtime\bg_watchdog.py`** puts itself into a Windows job object (so Stop can end
   every process the app starts, see [Process control](#process-control-and-stop)), registers
   the run in `tmp\running\` under the instance policy, sets the console's title, icon, colors
   and taskbar identity, opens the log file, and starts the app Python with
   `script_wrapper.py --config tmp\runs\<id>\wrapper.json`. It shows the app's output in the
   console; the wrapper writes the log. Output that bypasses Python's streams (native code, child
   processes) goes to `<log>.output.log` first, which the wrapper merges into the log as it
   arrives; the file is deleted after a normal end and kept as evidence otherwise. It waits for the app to end,
   unregisters, and calls `process_exit.py` with the outcome. In no-terminal mode a completion
   window only appears when something needs to be shown.
9. **`runtime\script_wrapper.py`** runs inside the app Python. It removes the launcher's
   variables from the environment, sets `sys.argv` (`args_for_main_py`) and `sys.path[0]` exactly
   like `python main.py`, sets up the log and the print/input prefixes, writes `ready`, and runs
   `main.py` with `runpy`. It records the outcome in `result.json` and, for exceptions
   (including `SystemExit` with an error code and errors in worker threads or Tkinter callbacks),
   a traceback report in `traceback.json` (format in `runtime\_pyapp.py`).
10. **`runtime\process_exit.py`** reads the report and applies the settings for the outcome:
    title, window colors, icon, sound, crash log, opening the log or `main.py`, keeping the
    window open. For a missing package it offers to install it and restart.

The app gets these environment variables: `PROGRAM_NAME`, `ICON_PATH`, `APP_ID` (its taskbar
identity), `PROGRAM_HAS_TERMINAL` (`1`/`0`), `LOG_PATH`, `WDIR_IS_SCRIPT_DIR`,
`CLOSE_AFTER_SUCCESS` and `CLOSE_AFTER_FAILURE`.

## The other shortcuts

| Shortcut | Target | What it does |
| --- | --- | --- |
| `Stop <name>` | `B\Q.bat` → `actions\stop_program.py` | Stops every running instance of this project copy (see below) and closes after a short countdown. |
| `<name> - Settings` | `B\S.bat <file>` | Opens the user settings file (`user_settings_path`). |
| `<name> - Edit Code` | `B\M.bat <file>` | Opens the file set in `main_script_path`. |
| `<name> - Logs` / `- Crash Logs` | `B\L.bat` / `B\C.bat <folder>` | Opens the log / crash-log folder. |
| `<name> - Tools` | `B\T.bat` → `scripts\dev_tools\main.py tools` | The dev tools that the people using the app may need (`USER_TOOLS` in `main.py`). |

Setup passes each "open" shortcut its resolved target. `bootstrap\open_file.bat` /
`open_folder.bat` then open it **without starting Python** (VS Code via its `Code.exe`, else
Notepad; Explorer for folders), so these shortcuts are instant. Only when no target was passed
(a log path relative to the start folder, or with date codes in its folder part) or the file is
missing do they fall back to `actions\open_file.py` / `actions\open_folder.py`. Setup records
the targets in `pyapp\generated\shortcuts_created_by_setup.json`; each start warns when the settings
no longer match them.

`Setup - run first and after moving folder.cmd` (project root) runs `actions\setup.py`: banner,
environment, then every enabled shortcut (project folder, Start Menu, Desktop), and removes the
shortcuts it created earlier that are no longer wanted. The `.cmd` files in
`code\pyapp\dev_tools` run `scripts\dev_tools\main.py <command>` ([dev tools](../dev_tools/README.md)),
and `code\pyapp\icons\*.cmd` run `actions\gen_icons.py`.

## The Python environment

`code/pyapp/generated` is the uv project directory. `developer_settings.py` is the only file people edit:

- `python_version` is the requested Python; `pyapp/generated/.python-version` records the one the
  project actually uses (written on the first start). A different `python_version` opens a
  migration menu (re-lock keeping versions, upgrade all, empty package list, keep, write back).
- `packages` is the dependency list. `pyapp/generated/pyproject.toml` is **generated** from it
  (`scripts/env/pyproject.py`) with `requires-python = "==X.Y.*"`. Its header records the list
  it was generated from, so a change made in the file itself (e.g. `uv add` in the package
  terminal) is copied back into `packages` instead of being overwritten.
- `pyapp/generated/uv.lock` pins every package with hashes; commit it together with the settings.
- `pyapp/generated/.venv` is the app's environment.

`ensure_environment()` (`scripts/env/venv.py`) runs on every start and by Setup and the dev tools:

1. **Fast path:** when `tmp/environment.ok` matches a fingerprint of everything below
   (project folder, interpreter, uv, `pyproject.toml`, `uv.lock`, `.python-version`, the venv's
   `pyvenv.cfg`, `python.exe` and `site-packages`), it returns immediately.
2. Otherwise, under `tmp/environment.lock`: regenerate `pyproject.toml`, `uv lock` when it
   changed (offline first), re-link `.venv` to the project's Python when the project moved
   (`uv venv --allow-existing`, keeps the packages, works offline) or rebuild it beside the old
   one when the Python minor version changed, then `uv sync --locked --inexact` (offline first),
   and write the new stamp.

Downloads happen only when needed. If the chosen uv cannot install the requested Python, the
newest uv is fetched to `%LOCALAPPDATA%\PyApp-Template\uv` (never on PATH), the install is
retried, and that uv is used from then on while it is newer. `scripts/env/uv.py: uv_environment()` builds uv's environment
variables and mirrors `set_uv_environment` in `resolve_runtime.py`; keep both in sync. Python
lookups run from the system temp folder, because uv would otherwise treat `pyapp/generated/.venv` as
"the" Python; project commands use `code/pyapp/generated`.

Self-contained folders (`make_self_contained` dev tool): uv in
`pyapp/generated/uv`, Python in `pyapp/generated/pythons`, the uv cache optionally in
`pyapp/generated/uv-cache` (not needed: packages are copied into `.venv`, not linked to the cache). The `.venv` is relocatable and re-linked after a
move, so a copied folder works offline on another PC.

## Process control and Stop

- **Registry.** `tmp/running/` holds one record per running watchdog
  (`scripts/runtime_state.py: ProcessRegistry`): PID, process creation time and executable (so a
  reused PID is never mistaken for the app), console window, app process, run folder and job
  name. A project-specific named Windows mutex serializes changes; it is never held while waiting.
- **Job objects.** The watchdog creates a Windows job and puts itself in it before starting the
  app, so every process the app starts (also grandchildren) belongs to the job.
- **Stop** (`actions/stop_program.py`, and `instance_policy = "replace"`) first asks each
  instance to close: `WM_CLOSE` to the app's windows, or Ctrl+C to its console
  (`runtime/send_ctrl_c.py`, a small detached helper, because a process can only send Ctrl+C to
  a console it is attached to). It writes `stop-requested` into the run folder, so the watchdog
  ends without sounds, menus or prompts. After `stop_timeout_seconds` the job is terminated
  (fallback: the process tree, via Toolhelp and `TerminateProcess`; no `taskkill`/WMI).
- **Taskbar identity.** Each project copy has its own AppUserModelID: program name plus a hash of
  program name and project folder (`scripts/shortcuts.py: project_app_id`). Setup stores it in
  the shortcuts (`scripts/com_tools.py`); the launcher sets it on its consoles and the app's
  process. The no-terminal shortcut uses the same ID plus `W`, and so does the completion window
  of a no-terminal launch, so each window groups with the shortcut that started it.
- `scripts/windows_focus.py` brings a running instance to the front (`instance_policy = "focus"`).

## Errors, tracebacks and completion

- **Expected problems** (`scripts/errors.py`): `SettingsError` (wrong setting),
  `SetupError` (uv/Python/download problems) and `LaunchCancelled`. `entrypoint.py` shows them
  as one red ERROR line without a traceback; mistakes inside `developer_settings.py` itself
  (syntax error, `Ture`, ...) are reported with their line number.
- **Unexpected errors** in a tool: the tool's `fail_message`, then the traceback.
- **Ignored errors** (cosmetic steps): `diagnostics.note_ignored()` appends them to
  `tmp/diagnostics.log` (the `status` dev tool shows the count; `PYAPP_DEBUG=1` prints them).
- **Exit codes** between the wrapper and the watchdog (`WrapperExit`) and between the watchdog
  and `process_exit.py` (`ExitMode`) are defined in `runtime/_pyapp.py`, with deliberately
  different numbers and an explicit mapping (`EXIT_MODE_FOR_WRAPPER_EXIT`).
- **Traceback reports.** The wrapper removes its own and `runpy`'s frames, so a report looks
  like `python main.py`. It stores CPython's formatting (used for exception groups) and a
  structured chain (cause/context, notes) with `traceback_lines_before` / `_after` source lines
  for the app's own files. `scripts/traceback_render.py` renders it: full paths as
  `path:line in function`, a `>` at the failing line, then the error and the script, time and
  Python details; in color on black so it stays readable on any window color, plain in crash
  logs.
- **Outcomes** (`process_exit.py`): `success`, `failure` (an exception, a non-zero exit, an
  interpreter crash such as an access violation, no report written, or a launcher error) and
  `keyboard_interrupt`. Each has `close_after_*` and `open_log_file_after_*`; success and failure
  have `play_sound_after_*`, and failure has `open_crash_log_after_failure`. Window titles are
  `TITLE_AFTER_*` in `backend_settings.py`. Failures turn the window black. Every non-success
  writes a crash log unless `enable_crash_log = False`.
- **Missing packages**: a `ModuleNotFoundError` for an import that is not one of the app's own
  modules offers to add the package (`uv add`), install it without recording it, find all
  imports (`scripts/import_finder.py`), open the package terminal, or quit; then it restarts.

## Console output

All launcher windows share one look (`scripts/console_tools.py`): `print_heading` (cyan
"── Title ──"), `print_step` ("» doing something"), `print_info` (grey notes),
`print_success` / `print_warn` / `print_error` (OK, !, ERROR badges), `ask`,
`wait_for_enter`, `print_choices` (numbered menus) and `print_fields` (aligned values). Colors
appear only on a real console, never in redirected output or log files. Windows that stay open
for a while (Setup, dev tools, installing Python or packages) start with the program name in
ASCII art (`scripts/banner.py`). The batch/Python bootstrap and the
`.cmd` files use the same badges.

## Every file

### Root of `DONT_CHANGE`

| File | Purpose |
| --- | --- |
| `README.md` | This document. |
| `CHANGELOG.md` | Changes per version; the newest heading matches `LAUNCHER_VERSION`. |
| `TODO.md` | Open items and ideas. |
| `LICENSE.md`, `LICENSES/` | License of this folder (`MIT OR Apache-2.0`) and of the bundled font. |
| `backend_settings.py` | Every internal path and constant (`LAUNCHER_VERSION`, folders, icon paths, file names, defaults). Imported by almost everything; changes nothing on import. |
| `ruff.toml`, `pyrefly.toml` | Lint and type-check settings for this folder only (Python 3.8, Windows, 120 columns). |
| `.gitignore` | Keeps `tmp/`, caches and `__pycache__` out of Git. |
| `tmp/` | Created at runtime, never committed: `runtime.cmd` (bootstrap cache), `environment.ok`/`.lock`, `bootstrap.lock`, `running/` (registry), `runs/<id>/` (per-run files: `wrapper.json`, `ready`, `startup.json`, `result.json`, `traceback.json`, `bootstrap.log`, `stop-requested`; deleted by a launch, Stop or Setup when no instance is running and the folder is at least 5 minutes old), `diagnostics.log`. Safe to delete while the app is not running. |

### `B/` – shortcut targets (short names keep the shortcut command line short)

| File | Started by | Does |
| --- | --- | --- |
| `W.bat` | the main shortcut | `start_program.py` with a terminal |
| `N.bat` | `(no Terminal)` shortcut | `start_program.py` without a terminal |
| `Q.bat` | `Stop` shortcut | `stop_program.py` |
| `S.bat`, `M.bat` | Settings / Edit Code | `open_file.bat <file>`, else `open_file.py` |
| `L.bat`, `C.bat` | Logs / Crash Logs | `open_folder.bat <folder>`, else `open_folder.py` |
| `T.bat` | Tools | `dev_tools/main.py tools` |

### `bootstrap/` – before any Python is known

| File | Purpose |
| --- | --- |
| `run.bat` | Runs `%PYAPP_ENTRY_SCRIPT%` through `entrypoint.py` with the launcher Python; pauses on bootstrap failures. |
| `ensure_runtime.bat` | Creates `tmp\`, loads the cached uv/Python paths or calls `resolve_runtime.py`; sets `PYAPP_UV` and `PYAPP_PYTHON`. |
| `..\run.bat` | The one file that scripts outside `DONT_CHANGE` start: `run.bat setup`, `icons`, `icons-help` or `dev <command>`. Everything else in this folder can move between versions. |
| `resolve_runtime.bat` | Gets any working uv and Python with tools built into Windows (`curl`, `tar`), then runs `resolve_runtime.py`. No PowerShell script, so policies that block those don't matter. |
| `resolve_runtime.py` | Reads the `[bootstrap]` settings, finds/installs uv and the project's Python, writes `tmp\runtime.cmd`. |
| `open_file.bat`, `open_folder.bat` | Open a file (VS Code, else Notepad) or folder without Python. |

### `actions/` – entry tools (each has a `main()`, run by `entrypoint.py`)

| File | Purpose |
| --- | --- |
| `start_program.py` | Launch: settings, instance policy, environment, run folder, starts and waits for the watchdog. |
| `stop_program.py` | The Stop shortcut. |
| `setup.py` | Setup: banner, environment, shortcuts (project folder, Start Menu, Desktop), removal of stale ones. |
| `open_file.py`, `open_folder.py` | Fallbacks of the "open" shortcuts (resolve the target from the settings). |
| `gen_icons.py` | Builds the `.ico` files in `code/pyapp/icons` from `icon.png` and the bundled overlays; asks per icon before replacing an `.ico` it did not make (`generated/auto_generated_icons.json`). |

### `runtime/` – the running app

| File | Purpose |
| --- | --- |
| `bg_watchdog.py` | Owns one run: job object, registry, console appearance, log, starts the wrapper, copies output, hands the outcome to `process_exit.py`. |
| `script_wrapper.py` | Runs inside the app Python: clean environment, `sys.argv`/`sys.path` like `python main.py`, logging and prefixes, runs `main.py`, writes the result and traceback report. |
| `_pyapp.py` | The protocol shared by wrapper and watchdog (exit codes, traceback reports). Imported in the app process as the top-level module `_pyapp`, a name that cannot shadow the app's modules. |
| `process_exit.py` | Completion handling per outcome; missing-package menu and restart. |
| `send_ctrl_c.py` | Helper that attaches to another console and sends Ctrl+C (graceful Stop of console apps). |

### `scripts/` – shared code

| File | Purpose |
| --- | --- |
| `entrypoint.py` | Runs every tool with one error, exit-code and "Press Enter" policy (`fail_message`, `pause_on_success`). |
| `config.py` | Loads `developer_settings.py` (filling in defaults for missing settings), validates every setting (all problems at once, with allowed values), checks the `[bootstrap]` rules and edits settings in place (keeps comments and CRLF). |
| `errors.py` | `SettingsError`, `SetupError`, `LaunchCancelled`. |
| `diagnostics.py` | Records deliberately ignored errors in `tmp/diagnostics.log`. |
| `console_tools.py` | Message styles, prompts, console title/icon/colors/taskbar identity, minimize/foreground, opening files in the editor. |
| `launcher_ui.py` | Launcher-level appearance (settings colors), tracebacks of tools, log paths, Stop of running instances. |
| `banner.py` | Reads the banner font and prints the ASCII-art program name. |
| `traceback_render.py` | Turns traceback reports into colored or plain text. |
| `runtime_state.py` | File lock, atomic JSON, process identities, the instance registry, job objects, process-tree termination, unique log names, interpreter-crash exit codes. |
| `instance_policy.py` | What to do when the app is already running (message boxes). |
| `windows_focus.py` | Finds and activates the windows of a running instance. |
| `shortcuts.py` | Creates `.lnk` files (via COM), their targets and taskbar identity, the record of created shortcuts, removal of stale ones. |
| `com_tools.py` | Minimal COM helpers with `ctypes` (GUIDs, property store, AppUserModelID). |
| `file_tools.py` | Safe folder removal (refuses paths outside the expected parent, junction-aware), path helpers, file-name sanitizing. |
| `image_tools.py` | PNG checks and ICO generation through Windows' own WPF (no Pillow). |
| `import_finder.py` | Offline import finder: scans the code folder with `ast`, drops the standard library and the app's own modules, maps imports to PyPI names (installed metadata, then `data/import_to_package.txt`, else a guess); imports guarded by `try/except ImportError` are optional. |
| `dev_tools/main.py` | Entry point of all dev tools: the command table, the menu, `NO_PAUSE`. |
| `dev/common.py` | Shared helpers of the dev tools (`confirm`, `prepare`, requirement names). |
| `dev/packages.py` | add, remove, upgrade, sync, find imports, package terminal, export requirements. |
| `dev/py_vers.py` | change_python, update_python. |
| `dev/self_contained.py` | make_self_contained. |
| `dev/housekeeping.py` | clean, remove_shortcuts, status, test. |
| `env/uv.py` | Which uv to use, its environment variables, running it. |
| `env/pythons.py` | Finding and installing Pythons with uv; `pyapp/generated/.python-version`. |
| `env/pyproject.py` | The generated `pyproject.toml`: render, parse, reconcile with `packages`. |
| `env/venv.py` | `ensure_environment()`, the fast-path stamp, building/re-linking `.venv`, lock and sync, Python switches, package actions, the package terminal. |

### Data, icons, tests

| Path | Purpose |
| --- | --- |
| `data/import_to_package.txt` | Import name → PyPI name for about 2,500 packages whose names differ; generated by the Dev Helpers' `make_import_map.py`. Your own pairs can be added at the end. |
| `pyapp_tools/` | Development tools for the launcher itself, `.bat` files whose code is in `pyapp_tools/src`: `verify_launcher` (Ruff, Pyrefly), `get_startup_time`, `get_import_times`, `make_import_map`, `show_longest_paths`. The launcher never uses them. |
| `data/dev_settings_default.py` | The settings file this version ships with: defaults for settings a project's `developer_settings.py` lacks (see [Versions](#versions)). Read with `ast`, never imported. |
| `data/fonts/` | Banner font (see [Licensing](#licensing)). |
| `data/icons/` | Bundled default PNGs (used when the project's PNG in `code/pyapp/icons` is missing or unchanged) and `HOW_TO_CHANGE_ICONS.txt`. |
| `tests/` | Regression tests for this folder; see `tests/README.md`. |

## Versions

`LAUNCHER_VERSION` in `backend_settings.py` is the version of this folder. It follows
Semantic Versioning, and each part also says what an update takes:

| Part | Means | Update by |
| --- | --- | --- |
| **PATCH** (1.0.**1**) | bug fixes and minor improvements (wording, speed, small fixes of behavior) | replacing the `DONT_CHANGE` folder |
| **MINOR** (1.**1**.0) | new features, nothing breaks | replacing `DONT_CHANGE`; new optional files outside it (e.g. a new dev tool `.cmd`) may be copied |
| **MAJOR** (**2**.0.0) | something breaks (a setting renamed or removed, a file moved) | replacing `DONT_CHANGE` and following the steps in `CHANGELOG.md` |

New settings never break an update: when a project's `developer_settings.py` lacks a setting,
the launcher uses its value from `data/dev_settings_default.py` (a copy of the settings
file this version ships with) and says so once; expressions like `f"{program_name}"` use the
project's own values. The dev tools that change a setting add a missing one to the file. The
bootstrap's fallbacks in `resolve_runtime.py` are the same values (checked by the tests).

The newest heading in `CHANGELOG.md` names the same version (also checked by the tests);
releases are tagged `v<version>` on GitHub. Setup and the `status` dev tool show the version.

## Tests, linting and type checking

- `tests/` holds the regression tests (about 10 s, offline, standard library only):
  `code/pyapp/DONT_CHANGE/tests/run_launcher_tests.cmd`, or `python run_regressions.py` in that folder.
  `test_windows.py` runs on Windows only. See `tests/README.md` for what each file covers.
- `ruff.toml` and `pyrefly.toml` apply to this folder only (the app's own code keeps the
  developer's settings). Run `ruff check`, `ruff format --check` and `pyrefly check` here; the
  `BLE001` permits catch-all excepts around cosmetic steps; other reviewed exceptions
  are documented beside narrow `noqa` directives, including Windows path behavior on Python 3.8.

Pyrefly uses its strict preset and targets Python 3.8. Existing overrides have
individual `missing-override-decorator` suppressions because `typing.override`
requires Python 3.12; the launcher keeps its standard-library-only runtime.

## Licensing

Everything here is `MIT OR Apache-2.0`. See [LICENSE.md](LICENSE.md).

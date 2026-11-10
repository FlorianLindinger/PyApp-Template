# PyApp-Template launcher changelog

Changes of this `DONT_CHANGE` folder. Versions follow Semantic Versioning as described in
README.md ("Versions"); `LAUNCHER_VERSION` in `backend_settings.py` names the current one.

## 0.0.1 - unreleased

The first versioned release; it contains every change below.

### 2026-11-10 - audit fixes

- `fresh_clone_test` no longer overwrites the real app when `main_script_path` is absolute: the probe goes to the clone's copy, and a path that leads outside the clone is refused.
- The `clean` dev tool deletes only the launcher's own log files (named after `log_path` / `crash_log_path` plus a run ID), so other files in a shared log folder are kept.
- Stop with a timeout also ends the processes an instance left running in its job when the instance itself closed in time.
- An exception in an `atexit` callback of the app now counts as a failure (Python 3.10 and newer).
- Typing several packages at the add prompt keeps version ranges, extras, markers and URLs whole, e.g. `numpy>=1,<2 requests[socks,security]`. Pasted requirements with `\` continuation lines and `--hash` options are read correctly.
- Settings edits escape line breaks and control characters, refuse `inf`/`nan`, and never write a `developer_settings.py` that is not valid Python. `stop_timeout_seconds` must be finite.
- The generated `pyproject.toml` stays valid with emoji and other characters beyond U+FFFF in a dependency.
- Corrected outdated paths and descriptions in the READMEs.
- The log now also contains the output of native code and child processes, in order with the prints. `.output.log` only holds that output, is written by the app process itself (so it survives a hard crash), and is still deleted after a normal end.
- If the watchdog fails after starting the app, it ends the app and its child processes instead of leaving them running unregistered.
- Package changes (dev tools, missing-package recovery, and a launch that has to sync the environment) are refused while the app runs, before anything is changed.
- A warning says when regenerating `pyproject.toml` drops `[tool.uv.sources]` (e.g. from `uv add --git`), and suggests a direct reference in `packages` instead.
- `make_import_map` reads cached projects again after 30 days (`--max-age-days`), or all of them with `--refresh`; the map's header says when the package data was read.

### 2026-11-08 - clearer development tools

- The tools in `tools/` use the launcher's headings, badges and aligned tables; `verify_launcher` ends with a summary of its checks and names the configuration files it uses.
- New `tools/check_git_leaks.bat` looks for secrets and personal data in the current files and the Git history.
- The dev tools: a grouped menu that waits before returning, a heading on every tool, a verdict in `status`, file counts in `clean`, and colored settings changes.
- The bootstrap no longer runs a downloaded install script or compiles code at runtime, which antivirus programs distrust. It checks downloads with Get-FileHash and falls back to `certutil` only where PowerShell is blocked. A global uv now comes from the checksum-verified download.
- Setup no longer runs a PowerShell script, so company policies that block those no longer stop it: `resolve_runtime.bat` gets uv with Windows' own `curl` and `tar`, and `resolve_runtime.py` does the rest. Company-policy and firewall problems now get a clear message.
- New `python_source = "system"` uses a Python already installed on the PC and downloads none.
- Renamed `code/backend` to `code/pyapp`, so that apps can have their own `backend` package. Run Setup once to renew the shortcuts.
- Scripts outside `DONT_CHANGE` now use one entry file, `DONT_CHANGE\run.bat`, so everything else in the folder can change between versions.
- New weekly GitHub Action for the template catches problems with the newest uv and Python. New tests guard the repository name in the Actions and the paths older projects rely on.
- New setting `github_actions`: with `"leaks"` in it, Setup adds a GitHub Action to the app that looks for secrets and personal data.
- Crash logs also contain everything the app printed, when logging is on. The raw `.output.log` is deleted after a normal end.
- The launcher no longer marks files and folders such as `.git` or `.gitignore` as hidden in Explorer.
- New `tools/release.bat` bumps the version, finishes the changelog and builds the zip; new `scripts/tools/git_hooks/pre-push` runs the leak check on the commits being pushed.
- New `tools/fresh_clone_test.bat` checks that a fresh clone of the current commit sets up and starts; new `tools/test_all_pythons.bat` runs the tests on Python 3.8 and the newest Python.
- The tools show a short message instead of a traceback for expected problems and Ctrl+C; `make_import_map` keeps the existing map when most of a download fails.

### 2026-11-08 - launcher fixes

- Editing a setting whose value is in parentheses on its own lines no longer damages `developer_settings.py`.
- The log now records what was typed at an `input()` prompt that ends with a line break.
- The `clean` dev tool keeps log files that are in use and the per-run diagnostics of running instances, instead of failing or breaking their completion report.
- A Ctrl+C while the app starts no longer ends its watchdog.
- A launch no longer fails if `startup.json` is briefly locked while the launcher reads it.
- The Windows regression tests also pass from a virtual environment and from shells that ignore Ctrl+C.
- `tmp\runs` no longer grows forever: a launch, Stop and Setup delete run folders at least 5 minutes old when no instance is running.

### 2026-11-08 - calmer error reports

- Error reports are one block between two rules: headline, frames, error, then the script, time
  and Python details (they used to sit above the traceback between two more rules). File names
  and the failing line's number stand out in color.
- Removed `traceback_colors`: tracebacks are colored in a terminal and plain everywhere else.
- One banner font: `future` is always used; `app_name_banner_font` and the fonts `future_smooth`,
  `standard` and `coder_mini` are removed.
- Removed `overwrite_log` and `overwrite_crash_log`: every run writes its own uniquely named file.
- Added `enable_crash_log` (default `True`): `False` stops writing crash log files.
- Crashes count as failures: every `*_after_crash` setting is merged into `*_after_failure`.
- Added `open_crash_log_after_failure` (default `False`; Ctrl+C does not count).
- `title_after_*` moved to `backend_settings.py` (`TITLE_AFTER_*`).
- Removed `open_main_py_after_*`, `terminal_colors_after_success`,
  `terminal_colors_after_keyboard_interrupt` and `play_sound_after_keyboard_interrupt`;
  `play_sound_after_*` are True/False only (no custom `.wav` paths).
- The `*_sub_icon_scale` / `*_sub_icon_alignment` settings moved to `backend_settings.py` (`SUB_ICONS`).
- Removed `allow_downloads_at_launch` and `PYAPP_ALLOW_DOWNLOADS`: launches may always download what is missing.
- Removed `package_environment` and `allow_installing_into_global_python`: the app always uses the project's `.venv`.
- `python_source` is `"local"` or `"uv_user"`: the two `system_...` options are removed, so uv always provides Python.
- If uv cannot install the requested Python, the newest uv is fetched to `%LOCALAPPDATA%\PyApp-Template\uv` (not on PATH) and the install is retried.
- Removed `max_log_files` and `max_run_folder_age_days`: logs and run folders are kept until deleted (dev tool `clean`).
- `install_environment_when_generating_shortcuts` moved to `backend_settings.py`.
- `packages` can also be a pasted requirements.txt in a `"""` block (comments and `--hash` are ignored).
- Added `environment_for_main_py`: environment variables set for `main.py`.
- The development tools moved in from the separate helpers repository: `tools/`, with their code in `scripts/tools/`.
- Added `main_script_path`: which file the launcher runs (default `..\\main.py`); it must be inside the code folder and not in `code/backend`.
- `main.py` runs in UTF-8 mode (`-X utf8`): `open()` without an `encoding` and `subprocess` text use UTF-8.
- The ignore rules for `code/backend` moved from the root `.gitignore` to `code/backend/.gitignore`.
- `open_main_py.ico` is now `open_code.ico`, and its overlay says OPEN CODE. Run Setup so existing shortcuts use it.
- `open_main_py_shortcut_name` is now `open_code_shortcut_name`, and the `desktop_shortcuts` kind `"main_py"` is now `"open_code"`.
- `shortcuts_created_by_setup.json` moved to `code/backend/generated`.
- Overlay images are always the bundled ones (the overlay PNGs in `code/backend/icons` are gone). `regenerate icons.cmd` updates the icons it made and asks, per icon, before replacing any other `.ico` (`generated/auto_generated_icons.json`).
- `pyproject.toml`, `uv.lock`, `.python-version`, `.venv` and the local `uv`, `pythons` and `uv-cache` moved to `code/backend/generated`, which the launcher
  creates; files in the old location are moved on the next launch. The `.gitignore` of older projects needs the new paths.

### 2026-11-07 - tracebacks, simpler icons and colors, tests and docs in DONT_CHANGE

- Tracebacks: every frame shows the file's full path as `path:line in function`; your own files
  get `traceback_lines_before` / `traceback_lines_after` source lines (replace
  `traceback_extra_lines`); bold red rules; drawn on black so their colors stay readable; the
  Python executable is listed. The error line names the error itself:
  `"main.py" failed: ZeroDivisionError: division by zero`.
- After a failure or crash the window turns black (`terminal_colors_after_failure` and
  `terminal_colors_after_crash` removed); the window colors change before anything is printed,
  so the colored lines keep their colors.
- Crash and Ctrl+C use the failure icon (`crash.ico`, `keyboard_interrupt.ico` and their
  sub-icon settings removed).
- Only the app's own window uses `terminal_bg_color` / `terminal_text_color`; Stop stays black.
- The completion window of a "(no Terminal)" launch groups with that shortcut on the taskbar.
- The regression tests moved into `tests/` (`tests/run_launcher_tests.cmd`); this changelog,
  TODO.md and a detailed README.md moved here too; `LAUNCHER_VERSION` added (shown by Setup and
  the `status` dev tool); `tmp/` is created by the bootstrap when it is missing;
  `icon_related/` renamed to `icons/`.
- Settings missing in a project's `developer_settings.py` (e.g. after a launcher update) use
  their defaults from `data/dev_settings_default.py` instead of failing; dev tools that
  change such a setting add it to the file. The bootstrap's fallbacks now match these defaults
  (`python_source`, `python_version`, `uv_user_python_visible_globally` differed).

### 2026-11-06 - structure, type checking, banner, consistent console output

Not committed; tested with the regression suite (62 tests), Ruff and Pyrefly 1.4.1 on Linux.
Windows-only paths (batch files, job objects, COM, Stop, real consoles) still need a Windows run.

#### Structure
- `scripts/uv_env.py` (~940 lines) split into `scripts/env/`: `uv.py` (running uv), `pythons.py`
  (find/install Python, `.python-version`), `pyproject.py` (generated `pyproject.toml`), `venv.py`
  (`.venv`, `uv.lock`, `ensure_environment`, package actions). `run_uv` returns the exit code;
  `run_uv_captured` returns (code, stdout, stderr).
- `scripts/dev_tools.py` keeps only the menu and the command table; the commands live in
  `scripts/dev/` (`packages`, `python_version`, `portable`, `housekeeping`, `common`). Commands
  that end on their own (menu, terminal) are listed in `NO_PAUSE` instead of changing a global.
- Merged: `process_tools.py` into `runtime_state.py`, `shell_tools.py` into `console_tools.py`,
  the icon table from `backend_settings.py` into `actions/gen_icons.py`.

#### Type checking and lint
- All 39 Pyrefly findings fixed without suppressions (settings passed explicitly instead of
  module globals set to None, `NoReturn` for the import-failure handler, typed dicts, one return
  type per function). `pyrefly.toml` also searches `runtime` (`_pyapp`).
- Ruff defaults: only `BLE001` (deliberate catch-alls, recorded in `diagnostics.log`) remains
  ignored; local timestamps use `datetime.now().astimezone()`.

#### Licensing
- `data/import_to_package.txt` is generated by `tools/make_import_map.py` from PyPI wheel
  file lists (no pipreqs data any more); generic folder names (models, utils, ...) are skipped.
- Banner fonts added as third-party exceptions: `standard.flf` (BSD-3-Clause, FIGlet),
  `coder_mini.flf` (MIT), `future.tlf` / `future_smooth.tlf` (WTFPL).

#### Console output
- `app_name_banner_font` (default `"future"`): program_name as ASCII art at the top of Setup,
  dev tools and first-time installs (`scripts/banner.py`, FIGlet/TOIlet reader with kerning).
- One message style for every launcher window (`console_tools`): section headings, `»` steps,
  grey notes, OK / ! / ERROR badges, numbered menus, `?` questions, aligned fields. Setup prints a
  per-shortcut summary; the status tool is grouped into sections; the bootstrap PowerShell and the
  `.cmd` files use the same badges.

#### Dev Helpers
- New layout: `tools/` (verify_launcher, get_startup_time, get_import_times,
  make_import_map, show_longest_paths), `future/` (ideas only), `archive/old_launcher/`
  (pre-uv files), `tmp/` (was `temporary/`). New tests: `test_banner.py`.
- Startup benchmark rewritten for the new launcher (temporary project copy with a probe main.py).

### 2026-11-05 - uv instead of the backend Python: bootstrap, environments, portability, shortcuts, instances

Branch `uv-bootstrap` (not committed). The embedded backend Python, the MSI-based Python
installer, pipreqs and rich were removed. uv now provides Python and all packages; the
launcher runs on the project's own Python in isolated mode. Everything below was tested on
Windows 11 (desktop of the developer PC) with uv 0.13.5 and 0.11.32 and with Python 3.8.20,
3.12.10 (system), 3.13.17 and 3.14.9.

#### Architecture

| Area | Before | Now |
| --- | --- | --- |
| Bootstrap | PowerShell on every launch installed/validated an embedded backend Python 3.12 + packages (rich, pipreqs, requests, docopt, ...), then a Python health-check import of rich/pipreqs on every start. | `bootstrap/ensure_runtime.bat` reuses a cached uv/Python lookup (`tmp/runtime.cmd`) without PowerShell. `bootstrap/resolve_runtime.ps1` runs only when `developer_settings.py` or `backend/.python-version` changed or a cached file is missing. |
| Launcher interpreter | Separate backend Python. | The project's Python, started with `-I -S -X utf8` (isolated, no `site`, standard library only, UTF-8 output). App packages cannot affect the launcher. |
| App Python | Full CPython assembled from python.org MSI components (ends with Python 3.16 per PEP 773). | `uv python install` (python-build-standalone builds, include Tcl/Tk). Location per `python_source`. |
| App packages | `pip --target code/backend/packages` + custom manifest (RECORD hashing on every start), `DEFAULT_PYTHON_PACKAGES.txt` with a magic "auto find" comment, custom lock JSON. | `packages` list in `developer_settings.py`; uv project in `code/backend`: generated `pyproject.toml` + `uv.lock` (with hashes) + `.venv`. Every start runs an offline `uv sync --locked --inexact`. |
| Import inference | pipreqs (backend dependency, online PyPI lookups, ran against the backend environment). | Own offline finder (`scripts/import_finder.py`): `ast` scan, exact stdlib list for the running Python (fallback for 3.8/3.9), local-module exclusion, installed metadata first, bundled mapping (`data/import_to_package.txt`, the former embedded 1,200-line string, now a data file), "guess" otherwise; `try/except ImportError` imports marked optional. |
| Tracebacks | Rendered with rich from a custom serialization (no exception notes/groups). | Standard library: launcher frames (wrapper, runpy) stripped so reports look like `python main.py`; `traceback.TracebackException` gives chains, notes and exception groups; context lines (`traceback_extra_lines`) for frames in your own code; ANSI colors in terminals (`traceback_colors`), plain text in crash logs. |

#### New and changed settings (`developer_settings.py`)

- New: `python_source` (`local`, `uv_user`, `system_if_matching_else_local`, `system_default_any_version`), `package_environment` (`project_venv`, `interpreter_site_packages`), `uv_prefer`, `uv_install_if_missing` (`global` via Astral's installer, `local` via GitHub download with SHA-256 check, `never`), `uv_version` (`""`, exact or range), `uv_user_python_visible_globally`, `uv_cache`, `allow_downloads_at_launch`, `use_system_certificates`, `allow_installing_into_global_python`, `start_menu_shortcuts`, `desktop_shortcuts`, `instance_policy`, `max_log_files`, `max_run_folder_age_days`, `traceback_colors`.
- `python_version`: `""` now means "newest stable, chosen once and kept" (move up with `update_python`); uv request strings such as `"3.14t"` work. Supported: everything uv offers, currently 3.8.2+ on Windows x64; clear errors for unsupported/unavailable versions (lists what uv offers).
- Renamed: `windows_terminal_shortcut_name` -> `terminal_shortcut_name` (it also covers the classic console), `install_python_when_generating_shortcuts` -> `install_environment_when_generating_shortcuts`, `PRINTED_ERROR_DATE_FORMAT` -> `error_date_format`.
- Removed: `install_tkinter` (uv's Pythons always include Tcl/Tk), `use_uv_to_install_packages` (always uv), `RICH_TRACEBACK_COLOR_THEME`, `prevent_start_if_already_running` / `close_already_running_instances_on_start` / `prompt_to_close_existing_instances` (replaced by `instance_policy`).
- `from __future__ import annotations` added so the `str | None` annotations work on Python 3.8/3.9.
- `[bootstrap]` settings must be one-line literals; `config.validate()` checks this and every other setting (types, choices, colors, shortcut kinds, Python version) and lists all problems with the allowed values. A syntax error in the file is reported as one readable line instead of a traceback.

#### Python version changes

When `python_version` differs from `backend/.python-version`, the launch (or `change_python.cmd`) offers:
1 switch + re-lock keeping versions, 2 switch + upgrade, 3 switch with empty dependency list (confirmation), 4 keep for this launch,
5 keep and write the current version into the settings, 6 cancel. The new venv is built beside the old one and swapped in only when it
works; `developer_settings.py`, `pyproject.toml`, `uv.lock` and `.python-version` are restored on failure. Minimized/hidden launches bring their console to the front for the menu.
`requires-python` is kept at `==X.Y.*` of the project's Python so the lock never forks.

#### Portability and recovery

- Moving/copying the project: the venv is re-linked to the project's Python with `uv venv --allow-existing` (keeps installed packages, works offline). Detection asks the venv's `python.exe` for its real base interpreter, because uv stores that path inside `python.exe`, not only in `pyvenv.cfg`.
- uv's minor-version junctions (`cpython-3.14-...`) that point nowhere after a move are removed by the bootstrap.
- Project commands use uv's "prefer managed" preference: with "only managed", uv re-checked the venv against interpreter details cached before the re-link and rebuilt it on the old location's Python.
- Unicode/space/apostrophe project paths: the runtime cache is UTF-8 (read with code page 65001); PowerShell decodes uv's output as UTF-8 (restored afterwards); launcher processes use `-X utf8`; piped app stdout/stderr are switched to UTF-8 by the wrapper.
- Missing global Python with `system_default_any_version`: falls back to a local install.
- `make_portable.cmd` copies uv, installs the Python locally, rebuilds the venv on it and offers the matching settings changes.

#### Dev tools

The 13 `.bat` + 13 `.py` package tools were replaced by one module (`scripts/dev_tools.py`) and small `.cmd` shims in `code/backend/dev_tools`:
`Dev Menu`, `add_packages`, `remove_packages`, `upgrade_packages`, `sync_packages`, `find_imports`, `package_terminal`, `change_python`,
`update_python`, `make_portable`, `export_requirements`, `status`, `clean` (logs, crash logs, run diagnostics),
`remove_shortcuts`. The old custom package console (pip/uv argument parsing) is replaced by a command prompt with the venv activated and uv on PATH.

#### Shortcuts and instances

- Setup also creates a Start Menu folder and optional Desktop shortcuts, records them in `code/backend/shortcuts_created_by_setup.json` and removes stale ones (renamed/disabled shortcuts, Desktop entries no longer wanted, empty Start Menu folder). Only shortcuts that point at this project's launcher, or at a project folder that no longer exists, are removed, so Setup in a copied project cannot delete the original's shortcuts. Desktop location via the shell API (OneDrive-redirected desktops).
- `instance_policy = "focus"` brings the running instance's window (app window, else console) to the front; instances without a window ask whether to replace them. All policy dialogs are shown without holding the registry lock (other launchers are no longer blocked for up to 120 s).
- App windows of no-terminal launches now group with a pinned no-terminal shortcut: Setup gave that shortcut the taskbar ID `<app>W`, but the launcher gave the windows the terminal shortcut's ID `<app>` (also wrong in the previous version). The suffix is one constant (`NO_TERMINAL_APP_ID_SUFFIX`) used by Setup and the watchdog; already pinned shortcuts work without re-pinning.
- Stop no longer uses `taskkill` (it failed on the developer PC because WMI is broken there, `HRESULT 0x80010114`); it terminates verified trees via Toolhelp snapshot + `TerminateProcess`.

#### Packages in developer_settings.py

- New setting `packages` (e.g. `["requests", "numpy>=2"]`) is the only place to declare the app's packages.
- The uv project moved from `code/` into `code/backend/`: `uv.lock` and `.python-version` (commit both), `.venv`, and
  `pyproject.toml`, which the launcher now generates from `packages` and the project's Python (ignored by Git).
- The generated file's header records the package list it was generated from. A change made to the file itself
  (`uv add`/`uv remove` in the package terminal, or the add/remove/find_imports dev tools, which use uv) is copied into
  `packages`; a change in `developer_settings.py` regenerates the file; if both changed, `developer_settings.py` wins
  with a warning. A file without that header (hand-written) is taken over only while `packages` is empty.
- The package terminal sets `UV_PROJECT`, so uv commands typed in `code/` use the backend project.
- `export_requirements.cmd` writes `backend/requirements.txt`. Option 3 of the Python migration menu empties `packages`.
- Tested in a Linux workspace with uv 0.11.32 and a local wheel index (settings -> file, `uv add`/`uv remove` -> settings,
  conflicts, missing `pyproject.toml` with an existing `uv.lock`, validation). Not yet tested on Windows.

#### Layout

- `DONT_CHANGE/settings/backend_settings.py` -> `DONT_CHANGE/backend_settings.py` (the `settings` folder is gone).
- Shorter paths: `scripts/actions` -> `actions` (`generate_icons.py` -> `gen_icons.py`, `open_crash_log_folder.py` ->
  `open_crash.py`, `open_log_folder.py` -> `open_log.py`), `scripts/runtime` -> `runtime` (`_pyapp_protocol.py` ->
  `protocol.py`), `scripts/setup` -> `setup`, `scripts/bootstrap` -> `bootstrap`, `temporary` -> `tmp`.
- `code/backend/shortcuts.manifest.json` -> `code/backend/shortcuts_created_by_setup.json`.
- Dev Helpers: `show_longest_paths.bat` lists the 30 longest paths in the template checkout and flags those over the Windows path limit.

#### Fixes from the 2026-11-05 review

- Missing-module recovery only for `ModuleNotFoundError`, uses the top-level name and refuses names of local modules (previously `from mymod import x` errors could install a same-named PyPI package).
- `sys.path[0]` is replaced (not prefixed) with the app folder, so the launcher's runtime folder is no longer importable from the app.
- Date placeholders are applied to the configured log path only (a `%` in the project path broke log paths).
- Exit codes are named constants shared by wrapper, watchdog and completion handler; the unreachable "exit mode 3" branch and its wrong comment are gone.
- The double environment lock in `start_program.py` and the test hook `PYAPP_TEMPLATE_ACTIVE_STARTUP_TIME_MEASUREMENT` were removed.
- Windows Terminal missing -> warning and classic console instead of a failed launch.
- Example `main.py` no longer crashes when the icon file is missing.
- Prints of the launcher are plain (no ANSI codes) when output is redirected; classic consoles get ANSI processing enabled explicitly.
- Log retention (`max_log_files`, `max_run_folder_age_days`).

#### Removed

`backend_python`/`backend_packages` handling, `ensure_backend_python.ps1/.bat`, `install_embedded_python.ps1`, `finish_backend_installation.py`
(including the embedded mapping string, an unused function and unreachable code), `check_backend.py`, `run_backend_script.bat`,
`backend_settings.ini`, `backend_packages.txt`, `backend_build_tools.txt`, `python_runtime.py` (MSI installer), `package_tools.py`,
`frontend_environment.py`, `environment_state.py`, `requirements_lock.py`, `git_tools.py` (unused), `scripts/dev_tools/*` (13 scripts),
`code/backend/dev_tools/*.bat` and `DEFAULT_PYTHON_PACKAGES.txt`, `delete_folder_safe` (~500 lines), dead helpers (`can_reach_url`,
`is_process_running`, `get_script_name`, `find_longest_paths`, `get_terminal_title`, `input_success`, `make_empty_args_safe`,
`do_stuff_when_not_normal_start`, ...), the legacy 11-argument wrapper protocol, legacy PID lock/`.stop` handling and the legacy traceback path.
Folders of the old template version on disk (`DONT_CHANGE/backend_python`, `backend_packages`, `backend/python`, `backend/packages`) are not touched by the launcher; delete them by hand.

#### Tested on Windows (2026-11-05)

Setup from scratch (uv found, Python 3.14.9 installed locally, venv, 14 shortcuts); hidden and terminal launches; failure with crash report;
missing-package recovery (add -> restart -> app runs); `status`, `add`, `remove`, `export`, `find_imports` (also on 3.8);
version switches 3.14 -> 3.13 -> 3.8 -> 3.14 with launcher and app running on each; `focus` policy (no second instance); Stop;
renamed shortcut and Desktop shortcut created and removed again; `update_python`; `make_portable`; portable copy in
`PyApp Moved O'Brien Ü 日本` with broken venv base (re-linked offline, Unicode output); local uv download with pinned
`uv_version = "0.11.32"` while the global uv 0.13.5 is newer; `system_if_matching_else_local` with system Python 3.12;
`system_default_any_version` + `interpreter_site_packages`; settings syntax error message.
Not tested interactively: the `prevent`/`ask`/no-window dialogs, the migration menu inside a minimized hidden-launch console,
the missing-package menu inside a terminal-launch window, `clean.cmd`, Windows Terminal mode, ARM64.

#### Notes

- The Dev Helpers regression tests target the removed backend and need to be rewritten for the uv layout.
- The template ships no `pyproject.toml`, `uv.lock` or `.python-version`; they are created in `code/backend` on the first run. App projects commit `uv.lock` and `.python-version`.


### 2026-10-31 ? Launcher reliability, maintainability and Tkinter example

This entry covers the numbered project review (1?38) and the follow-up requests
for focused helpers, shared entry handling, clearer documentation, a regression
matrix, cooperative Stop, and a Tkinter example. The updated source was inspected
before editing; its existing shared-package `.pth` repair was retained.

#### Numbered review changes

| Review | Previous behavior | Behavior after this change |
| --- | --- | --- |
| 1 | Normal starts selected the diagnostic stand-in. | `use_standin_main_script` defaults to False; normal starts run `code/main.py`. The stand-in and startup benchmark remain explicit diagnostics. |
| 2 | The documented setup `.cmd` was absent; older shortcuts could refer to an obsolete launcher. | Added root `Setup.cmd`, `Start.cmd`, the play-button `.cmd` setup alias, and a compatibility batch at the older launcher path. Text entry points resolve from their own location. |
| 3 | The launcher registered itself before checking existing instances. | Existing-instance checks and registration share one process lock, exclude the current PID, and happen in the correct order. Two simultaneous single-instance starts produce one app and one acknowledged cancellation. |
| 4 | Bare PIDs could identify unrelated reused processes. | Registry records contain executable image and Windows process creation time. Stop revalidates identity and retains the original process handle during escalation. Legacy bare PID files are never termination authority. |
| 5 | Helpers terminated their parent CMD/PowerShell to dismiss a window. | `close_terminal()` exits only the Python process; batches use `exit /b`. Generated command-shell shortcuts use `/c`, so their own consoles close naturally. An existing caller shell is preserved. |
| 6 | Terminal startup became `wt`/`conhost`, while logging checked only `terminal`. | Logging tests the resolved terminal modes. Terminal and hidden logging settings now select the corresponding run logs. |
| 7 | The package-success marker was created before pip/uv completed. | Installation happens in staging; dependency validation, inventory and manifest writing complete before publication. A failed install retains the previous packages and marker. |
| 8 | Runtime recreation deleted the working Python before downloading its replacement. | A sibling runtime is downloaded, extracted, signature-checked and probed first. Replacement keeps the old runtime during version/package migration and restores it if package preparation fails. Existing files are not deleted to begin a download. |
| 9 | Some deletion callers ignored a False/cancel result. | Explicit deletion helpers raise on cancellation. The low-level installer also checks cancellation. Directory replacement refuses linked paths and conflicting retained backups. |
| 10 | Reinstall option 6 was accepted but never executed. | All menu choices have executable branches. Added exact-version preservation (7) and explicit launch cancellation (8). A successful change continues the pending launch, so a second restart is unnecessary. See the menu below. |
| 11 | `main.py` received internal launcher flags and paths in `sys.argv`. | The wrapper consumes a private JSON configuration and sets `sys.argv` to the app path plus app arguments only. Shortcut arguments and configured defaults are combined without replacing literal `__EMPTY__` app values. Launcher metadata is not automatically added. |
| 12 | Active settings exposed unimplemented controls; app argument defaults were unused. | `args_for_main_py` is validated and connected. `supress_keyboard_interrupt`, `highlight_window_on_first_print`, and the proposed opt-in metadata setting are kept in `future/developer_settings.py`; production does not import them. |
| 13 | Instances shared startup signals and traceback JSON. | Each launch gets a UUID directory containing its config, readiness, startup acknowledgement, completion status, traceback and bootstrap diagnostics. A run cannot acknowledge or delete another run's crash report. |
| 14 | A thread lock protected a shared PID file only inside one process. | Atomic per-launcher records replace the shared read/modify/write PID list; policy and Stop operations use a process-shared Windows file lock. |
| 15 | Concurrent setup could recreate the same runtime/packages. | Startup handoff and public environment mutations use a reentrant interprocess environment lock. Backend bootstrap has its own OS-held file lock. Environment changes refuse to replace files belonging to registered running apps. |
| 16 | Startup was acknowledged before argument/script/child validation. | The wrapper initializes logging, app arguments, shutdown support and execution state before creating readiness. The watchdog acknowledges that run only after its child is ready, or records a startup failure. |
| 17 | Watchdog failures asked for a traceback that had never been saved. | The original exception is serialized, a plain-text traceback is retained, and startup failure includes its reason. Presentation failure does not erase the saved evidence. |
| 18 | The frontend did not enable faulthandler by default. | The actual app interpreter starts with `-X faulthandler`; the wrapper enables it and directs native diagnostics into the run log when logging is active. A deliberate child access violation is tested. |
| 19 | The wrapper closed logs before app atexit callbacks. | Logging cleanup is registered before app callbacks and runs after them. Shutdown prints remain captured and faulthandler is disabled before its log descriptor is closed. |
| 20 | Replaced streams lacked binary/standard-stream capabilities; native and child writes bypassed text logging. | Stream adapters expose a binary buffer and delegate remaining stream attributes. A raw combined-output companion is captured by the watchdog, including inherited child and native writes. See capture boundaries below. |
| 21 | Second-level filenames and overwrite mode could collide. | Both normal and crash log paths include the unique run ID, including custom filenames without timestamp directives. |
| 22 | Successful completion wrote a crash-log file. | Success performs configured completion actions without writing a crash report. |
| 23 | Text crash logs used the Windows default encoding. | Crash reports explicitly use UTF-8, as do configuration, status and ordinary text logs. |
| 24 | Hidden successful runs opened a completion console. | When `close_after_success=True`, hidden success runs completion actions without conhost. Failures that need acknowledgement/recovery are still presented visibly. Instance replacement confirmation in hidden mode uses a Windows dialog instead of invisible console input. |
| 25 | The sample ended with console `input()` despite a hidden launch mode. | Replaced it with a real Tkinter task list that works through terminal and no-terminal launchers. It has no console-input dependency. |
| 26 | Float zero could be classified as successful SystemExit; abrupt codes collided with wrapper codes. | Only None or integer zero (including False) is success. Completion has a separate report, so abrupt `os._exit(0..4)` cannot masquerade as handled wrapper status. Native status is preserved separately. |
| 27 | `show_traceback_locals` could not work with the serialized frame data. | Removed it from active settings/rendering and moved the proposed setting to `future`. Frame locations, source lines and exception chains remain available. |
| 28 | Batch `cd` discarded the shortcut's original working directory. | The launch directory is captured before backend work, generated shortcuts set Start in, and the selected app/log CWD uses that captured directory. The folder component of a formatted log path is also resolved correctly. |
| 29 | ?100%-isolated? overstated isolation and inherited Python/package-tool overrides. | App interpreters run with `-E -s`; launcher-created Python/package processes use a sanitized environment. Documentation states local dependency isolation and ordinary user permissions, rather than an OS sandbox promise. |
| 30 | Global execution and local recovery modified different interpreters. | Global mode resolves one actual interpreter path. Recovery names that path and gives a manual installation command; it does not change the managed local environment on its behalf. |
| 31 | Runtime and marker existence were treated as health checks. | Runtime checks execute imports of required stdlib/native modules and optional Tkinter. Backend checks import its runtime modules and compare exact package versions. Package state compares metadata/RECORD fingerprints and checks installed payload existence. Empty legacy markers migrate through additive staging to preserve manually installed packages. |
| 32 | Requirements edits did not invalidate installation state. | JSON state includes the requirements fingerprint, actual Python version and package inventory. Nested local `-r`/`-c` files participate. Changed requirements or damaged payloads trigger validated staging; remote includes are rejected for startup fingerprinting. |
| 33 | Static import inference was treated as an authoritative reset policy. | Inference defaults off. Explicit developer/recovery scans display their proposals and require review before installation. Declared requirements are the normal input; changing defaults is deliberate. |
| 34 | Versioned import scanning omitted the backend exclusions. | Versioned and unversioned scans now receive the same configured project exclusions. |
| 35 | Fresh setup could resolve different Python/packages/bootstrap tools and downloads lacked a recorded manifest. | Added exact runtime/default-package locks, seeded the runtime lock from the installed Python 3.14.6, retained signed-runtime bundled pip, pinned backend pip bootstrap, checked its published SHA-256, required artifact hashes for pinned backend requirements, and recorded Python download URLs/hashes. See reproducibility limits below. |
| 36 | Apostrophes in PowerShell source-interpolated paths broke extraction. | Extraction and bootstrap use `.ps1` parameters, environment arguments or literal-path APIs. User paths are not interpolated into quoted PowerShell source. Existing install destinations are refused, never recursively erased by the generic downloader. |
| 37 | MSI error logs lived inside an automatically deleted temporary download directory. | MSI logs persist under `temporary/installation-logs`. Failed backend staging folders and manifests are retained and their paths are printed. |
| 38 | ?Windows-only? hid an AMD64-only implementation. | Documentation explicitly says Windows x64. Managed installers check architecture before downloading/replacing a runtime and explain that native ARM64/x86 installation is unsupported. This change does not claim new native architecture support. |

#### Reinstall menu and restart behavior

- **0:** Keep current Python/packages for this launch.
- **1:** Change Python and install the declared defaults.
- **2:** Change Python and publish an empty package environment.
- **3:** Change Python and re-resolve the currently installed package names.
- **4:** As 3, then save resolved versions as defaults.
- **5:** Change Python, review inferred imports, then install them.
- **6:** As 5, then save resolved versions as defaults.
- **7:** Change Python while preserving exact current package versions. An incompatible
  version set fails visibly and rolls back; it is not silently relaxed.
- **8:** Cancel the launch and retain the current environment.

The menu runs before `main.py`. A successful choice continues that launch;
launching a second copy as a ?restart? would be redundant. Missing-package recovery
runs after the app has exited and therefore explicitly starts a new run after
successful recovery. Application arguments and the original launch folder survive
that recovery restart.

#### App arguments and deferred metadata

`args_for_main_py` supplies defaults. Shortcut arguments are appended. For example:

```text
Start.cmd --title "My tasks" --data-file "C:\Data files\tasks.json"
```

For a generated shortcut, keep its existing launcher and app-ID and append:

```text
-- --title "My tasks" --data-file "C:\Data files\tasks.json"
```

The first separator is consumed by the launcher. `main.py` receives only the app
path and app arguments. Terminal mode, protocol paths, app IDs and other launcher
controls are not positional arguments or injected metadata environment variables.
The possible opt-in metadata API remains deferred in `future`, defaulting off.

#### Focused helpers and shared entry handling

The former 2,641-line `generic_helpers.py` is now a compatibility import facade.
Its implementations live in `console_tools`, `filesystem_tools`, `process_tools`,
`python_runtime`, `package_tools`, `image_tools`, `git_tools`, and `shell_tools`.
`common_code.py` is also a facade: launcher appearance/path policy belongs to
`launcher_ui`, while frontend repair/package lifecycle belongs to
`frontend_environment`. `runtime_state` and `environment_state` own cross-process
state and transactional replacement. New production imports use the owning module.

Ordinary developer/icon/settings/log/shortcut tools use `entrypoint.run_file`.
It catches import-time failures as well as main failures, reports once, returns a
failure status, treats KeyboardInterrupt as 130, and owns acknowledgement prompts.
Twenty-eight batch entry points use `run_backend_script.bat`. Existing verifier
rescan loops retain their explicit loop interaction. The app wrapper/watchdog/exit
handler retain their distinct completion protocol; the exit handler now returns 1
when its own handling fails rather than returning a misleading successful status.

#### Cooperative Stop and the Tkinter example

Added `code/backend/shutdown.py`, a Python-3.5-compatible optional API using Windows
named events scoped to the child's PID and process creation time. No automatic
metadata arguments are needed:

- UI apps poll `shutdown_requested()` through their UI event loop.
- Other apps can call `register_shutdown(callback)`; callbacks run on a daemon thread.
- Stop validates the child identity, requests shutdown, and waits up to
  `graceful_stop_timeout_seconds` (default 5). `force_stop_after_timeout` controls
  whether a verified unresponsive tree may then be forcibly stopped.
- Cooperative termination bypasses normal exit acknowledgement so Stop does not
  leave an avoidable completion window behind.

The new `code/main.py` task list provides themed widgets, keyboard shortcuts,
add/complete/remove actions, atomic UTF-8 persistence, clear save/load errors,
`--title`/`--data-file` app arguments, and safe UI-thread shutdown polling. Invalid
existing task data is preserved. Local example data under `code/data` is ignored
by Git. Multiple instances sharing one file have last-writer-wins semantics; use
the single-instance setting or separate `--data-file` paths when that matters.

Polling from the UI thread follows the official
[Tkinter threading/event-loop guidance](https://docs.python.org/3.14/library/tkinter.html#threading-model).

#### Isolation, dependency state and reproducibility boundaries

Managed apps ignore Python environment overrides and user-site packages. Ordinary
application/proxy variables remain available. This is dependency isolation, not a
security boundary against application code. Global Python is deliberately external
and is not automatically repaired by modifying the local runtime.

`code/backend/frontend-python.lock.json` records the exact Python resolution for
its requested version/components. The default dependency `.lock.json` records
resolved pins and the source requirements fingerprint; commit both with releases.
Changing the declaration invalidates its lock. Backend exact pins are expanded
into hash-required installation requirements and artifact manifests during staging.
Python MSI publishers are checked through Windows Authenticode, and the embedded
runtime's executable/native modules are checked before use.

Frontend version locks are not universal hash locks, and third-party source builds
are not promised bit-for-bit reproducible. External artifacts can disappear.
Preserve a prepared folder for offline distribution. A newly missing package is
not guessed and installed without an explicit recovery choice/review.

#### Logging and operational boundaries

Normal logs include Python text/input and atexit callbacks. The `.output.log`
companion captures combined raw stdout/stderr, including binary/native output and
children that inherit those streams. Detached children that redirect their own
streams are outside that capture. When logging is enabled the app's stdout/stderr
are pipes; a program requiring an actual terminal should disable that terminal
logging setting. Native faulthandler output is retained in its configured log.

Run directories, retained failed staging folders, and MSI logs are persistent
for diagnosis; automatic retention/pruning is not implemented in this change.
If a `.previous` backup remains because Windows held files open, installation
reports it and refuses to overwrite that backup.

#### Documentation and regression validation

Rewrote the README introduction around the user's purpose and a short setup path.
Corrected developer-tool locations, removed the nonexistent pyproject.toml claim,
removed the unimplemented configurable crash-handler claim, documented real launch
arguments/isolation/platform support, and replaced the obsolete startup timing
claim with instructions to measure the health-check-based startup.

`tests/REGRESSION_MATRIX.md` maps first setup, moved/Unicode paths, simultaneous
starts, failed installations, terminal modes, exits, exceptions, Ctrl+C, native
crashes, cooperative Stop and Tkinter to automated tests or explicit manual release
acceptance procedures. `tests/run_regressions.py --native-crashes` enables a deliberate
fault only in a disposable child process.

Final validation results follow. Clean-VM network
installation, physical Ctrl+C delivery, taskbar grouping and visible Windows
Terminal behavior remain manual release checks; mocked dispatch is not represented
as a completed UI test.

#### Final validation results (2026-10-31)

- Managed frontend **Python 3.14.6**: **45 tests passed**, including the opt-in real
  native access violation, actual watchdog/wrapper handoff, Windows shutdown event,
  real batch argument forwarding, Unicode/apostrophe folder moves, simultaneous
  allow/prevent launches, hidden real Tkinter widget workflow, and offline fixture
  wheel installation. No tests skipped in that run.
- Embedded backend **Python 3.12.10**: the earlier 43-case suite passed with two
  expected skips (the deliberately disabled native-fault option and unavailable
  Tkinter). Final import smoke testing loaded **55 script modules** with zero
  failures. The dedicated startup probe is intentionally excluded from import
  smoke testing because it is an executable measurement fixture.
- Ruff undefined-name/import checks (`--select F`) passed; changed Python files
  were Ruff-formatted. Production scripts parsed successfully, PowerShell scripts
  passed parser validation, and `git diff --check` passed.
- Frontend wrapper, public shutdown API and Tkinter example passed the Python 3.5
  grammar check. This is syntax validation, not a claim of executing the suite on
  an installed Python 3.5 interpreter.
- The real existing-backend health/adoption PowerShell path passed without
  downloading or replacing the production environment.
- Final follow-through also made requirements fingerprints independent of CRLF/LF,
  handled compact/quoted includes and inline comments, and removed argument parsing
  at import time from the import benchmark. The benchmark now passes paths as argv,
  including apostrophes and Unicode, rather than embedding paths in Python source.

Cold clean-VM downloading/installing and the visible Windows Terminal/taskbar/
physical-Ctrl+C acceptance rows have **not** been executed in this session. They
remain explicitly marked manual in the matrix. Production environments were not
reset to run the regression suite; installation tests used temporary fixture targets.

#### Developer helpers relocated (2026-10-31)

Relocation validation: all **45 tests passed again from Dev Helpers**, against the
selected source checkout, with native crashes and Tkinter enabled. The optional
stand-in resolves to the moved backend_tools folder. Diagnostic/template batch
launchers now locate the source explicitly; source Ruff F checks and Git whitespace
checks pass. These checks do not replace the matrix's manual cold-VM/UI acceptance.

Final moved-launcher smoke checks: the module-import benchmark succeeds both with
its default backend module list and with explicit run-count/source/module arguments.
Its default code directory now points to the selected checkout rather than two
parents above Dev Helpers. Explicit arguments replace the defaults. The package
import launcher also succeeds and now returns failure immediately if any selected
import fails, so a later successful import cannot hide an earlier failure.

#### Setup reports its result and stays open (2026-11-01)

The root `Setup - run first and after moving folder.cmd` now prints its purpose
and the reminder to rerun after moving or renaming the project or a parent folder.
It executes shortcut setup in a separate command process, captures the exit code,
reports success or failure/crash, and always pauses before returning that same code.
The child shell isolates even a plain `exit` in an inner batch file. Inner Python
and batch acknowledgements are suppressed only for this outer launch through the
local `PYAPP_ENTRYPOINT_NO_PAUSE=1` environment variable, avoiding duplicate prompts;
direct launches retain their existing acknowledgement behavior. Terminating the
outer shell or closing its window cannot be caught by this mechanism.

Validation: temporary batch fixtures in a path containing spaces and an apostrophe
passed for success (0), failure (23), and a child-shell `exit` (17). All reached the
final prompt, printed the correct result, and preserved their exit code. A focused
check confirmed inner prompt suppression and normal direct-launch prompting.
Git whitespace checks passed. No production setup/install was run for these checks.


#### Remove application arguments from shortcuts (2026-11-01)

Generated Start shortcuts no longer forward appended arguments (including the
previous `-- --title "My Tasks"` syntax) to main.py. Start.cmd also stops forwarding
extra arguments. Removed the shortcut-argument JSON environment transport, watchdog
merge, and recovery-restart forwarding. Legacy PYAPP_MAIN_ARGS values are ignored;
only args_for_main_py in developer_settings.py supplies application arguments.
README/settings comments now describe this behavior. Existing customized shortcuts
need no regeneration: appended arguments no longer reach the application.
Regression coverage checks ignored shortcut arguments for all terminal modes and
verifies a real watchdog run still receives configured arguments while ignoring the
legacy environment payload.
Validation for shortcut argument removal: all 45 regression tests passed, including real watchdog argument isolation, terminal dispatch, Tkinter, and native-crash coverage. Git whitespace checks passed.


#### Remove use_standin_main_script (2026-11-01)

Removed the backend setting and both watchdog branches that selected an alternate
main script and injected diagnostic PROGRAM_HAS_TERMINAL/PROGRAM_NAME/ICON_PATH
environment variables. Normal launches now always select the application's main.py.
Removed the obsolete developer stand-in script and unused PYAPP_DEV_HELPERS_DIR
exports/documentation. The dedicated startup benchmark probe remains independent
and available only through the existing startup measurement workflow.
Validation: all 45 regression tests passed after stand-in removal, including real application launches, Tkinter, and native-crash coverage. No active references to the removed setting or diagnostic paths remain; Git whitespace checks passed.


#### Move template-development settings into Dev Helpers (2026-11-01)

Moved BACKEND_VERIFICATION_* and startup benchmark settings from production
backend_settings.py to Dev Helpers/helper_settings.py. Moved their diagnostic
implementations (backend verifier, import/startup benchmarks and startup probe)
beside the existing Dev Helpers launchers and updated launchers/test paths.
Source checkout discovery uses PYAPP_TEMPLATE_ROOT or the sibling-folder default;
benchmark marker files now belong to Dev Helpers/temporary. Runtime imports no
helper settings; its existing private startup-measurement protocol receives the
probe path from the benchmark tool instead of a production setting. Application
FRONTEND_VERIFICATION_* and shared runtime paths stay in the template because the
distributed app-development commands and launcher need them.
Validation: all 45 regressions pass from Dev Helpers, including native crashes and
Tkinter. The relocated import benchmark batch passes. Backend verifier and startup
benchmark CLI help load successfully. A real startup benchmark completed against
the managed Python and hidden start_program launcher using the external probe.
Ruff F checks and Git whitespace checks pass. Full backend lint/type verification
was not rerun; the verifier's settings import and CLI were checked.

#### Explain backend staging paths (2026-11-01)

Expanded the comments and docstring for _staged_path in backend_settings.py:
why installer subprocesses need temporary runtime/package paths, the normal-path
fallback, a concrete staging path example, containment/link checks, and the division
of responsibility between this path selector and PowerShell installation/rollback.
Documentation only; runtime behavior unchanged. Python syntax and Git whitespace
checks passed.


#### Simplify the Tkinter example (2026-11-01)

Replaced the task-list application with a minimal window titled "Example GUI"
containing only an "Example GUI" label. Removed task management, persistence,
argument parsing, custom styling, and icon setup. Kept the small root.after poll
for the Stop shortcut so cooperative shutdown still closes on the UI thread.
Existing task data is left untouched. Updated README and regression matrix;
the GUI regression now checks the real window/label and cooperative closing.
Validation: all 45 regressions passed, including the simplified real Tkinter window and cooperative close. The suite required execution outside the sandbox after pip encountered a sandbox permissions error reading the managed packages folder; no permissions or production environments were changed. Ruff F and Git whitespace checks passed.


#### Keep shutdown support inside DONT_CHANGE (2026-11-01)

Moved code/backend/shutdown.py to code/backend/DONT_CHANGE/scripts/shutdown.py,
with no compatibility file at the old location. Updated the example, wrapper,
process registry, regression imports and documentation. The relocated wrapper
test now obtains shutdown.py through its normal scripts-folder copy.
Graceful Stop, UI-thread polling, worker callbacks, timeout and force policies
remain unchanged. Application imports now use backend.DONT_CHANGE.scripts.shutdown.
Validation: all 45 regression tests passed after relocating shutdown.py, including real callback/UI shutdown and Unicode folder moves. Ruff F and Git whitespace checks passed.


#### Defer the whole graceful shutdown feature (2026-11-01)

Moved the Windows event API, timeout/force settings, registry integration reference
and cooperative regression snippets to future/graceful_shutdown (settings in
future/developer_settings.py). Removed active wrapper initialization, GUI polling,
registry request/wait/escalation, and stop-marker handling. Stop now directly runs
taskkill /T /F only after checking the registered process identity, retaining the
verified handle. Failed termination remains reported and the record is retained.
The GUI is a plain Tkinter window with no backend import. Updated documentation
and replaced cooperative tests with direct Stop success/failure checks.
Validation: all 45 active regression tests pass after deferring graceful shutdown, including direct Stop success/failure, stale identity protection, normal GUI close, portable paths and native crashes. Ruff F and Git whitespace checks passed.


#### Remove PID artifacts when the last instance closes (2026-11-01)

Replaced the registry's disk lock with a path-derived Windows named mutex, so
registry synchronization no longer leaves a .pid.lock file. All registration,
inspection, removal and Stop operations use that mutex, including the atomic
check/register sequence during simultaneous launches. Final exit/Stop removes
the empty .pid.d directory, obsolete .stop markers, abandoned atomic-write .tmp
files, and legacy .pid/.pid.lock files. Live instance records are preserved;
failed Stop keeps its record. Unknown files are never recursively deleted.
Hard-killing the watchdog itself can leave a stale record; the next launch or
Stop/registry inspection validates and cleans it. A legacy lock still held by an
older launcher cannot be removed until that older process releases it.
Added final-exit/multi-instance/mutex regressions and cleanup assertions to real
watchdog, direct Stop and simultaneous-launch tests.
Validation: all 48 tests passed, including new registry cleanup, real two-process
last-instance behavior, mutex exclusion/reentrancy, real watchdog exits, and
simultaneous launch cleanup. Ruff F and Git whitespace checks passed. Registry
inspection of the actual checkout found no live instances and left no PID
artifacts. No application processes were stopped by that inspection.

#### Keep production READMEs self-contained (2026-11-01)

Removed mentions of deferred/future functionality and the Dev Helpers repository
from the root and backend-internals READMEs. Retained the description of current
Stop behavior. Verified no such references remain in project README files;
Git whitespace checks passed. Documentation only; no runtime changes.


#### Remove compatibility import facades (2026-11-01)

Deleted scripts/generic_helpers.py and scripts/common_code.py. They contained
only re-exports, not implementations. Updated check_longest_paths to import
ANSI_RESET from console_tools, the regression to use console_tools directly,
and the import benchmark default to measure frontend_environment. Removed the
README facade claim. Focused modules now provide all current imports directly;
older external extensions must update imports to the module owning each helper.
The separate B/helper_scripts/generic_helpers installer directory is unrelated
and remains in use.
Validation: all 48 regression tests passed; all 49 remaining production script modules imported successfully; the updated default import benchmark passed. Ruff F and Git whitespace checks passed, and no active facade imports remain.


#### Organize backend batch and Python entry points (2026-11-01)

Renamed B to batches, replaced single-letter launchers with descriptive names
under batches/app, grouped bootstrap/setup/icon launchers, and grouped developer
tools by packages/Git/verification/paths in both batch and Python directories.
Python app actions now live in scripts/actions; watchdog, completion handler and
frontend wrapper share scripts/runtime instead of shortcut_targets/childs/frontend.
Reusable focused modules remain directly under scripts. Normalized package-tool
suffixes to underscores and removed the unused setup launcher trampoline.
Updated settings, imports, relative batch paths, root launchers, documentation
and external developer launcher/test paths. Existing shortcuts require regeneration
because their targets moved; setup remains the root entry point.
Validation: all 48 regressions passed after the move. All 49 production Python
modules import; all 75 static batch dispatch paths resolve. PowerShell parser,
Ruff F and Git whitespace checks pass. The relocated backend bootstrap completed
successfully using the existing environment. Regenerated seven app shortcuts
without reinstalling Python/packages and verified their targets. Setup success/
failure/pause fixtures pass in a path containing spaces and an apostrophe.
A simultaneous-launch fixture wrote to one shared append file and failed once;
its rerun passed. Replaced that shared file with per-process startup markers to
remove fixture write contention; the full suite then passed. No old compatibility
batch stubs remain. Historical deferred implementations were not rewritten.


#### Preserve compact shortcut batch targets (2026-11-01)

Restored the intentionally short B/W, N, Q, S, L, C and M.bat targets instead
of batches/app/descriptive-name.bat. Short targets reduce the command length in
Windows shortcuts when the checkout lives under a long path. Updated their
internal dispatch paths, settings, regression fixture and layout documentation.
Other batches and Python implementations retain the new purpose-based layout.
These are the actual dispatchers, not additional compatibility wrappers.
Validation: all 49 regressions passed, including a new guard limiting app shortcut targets to seven characters relative to DONT_CHANGE, and real W/N batch argument/quoting checks. Regenerated all seven shortcuts with compact targets; all static batch paths resolve and Git whitespace checks pass.


#### Use project identity in the minimal GUI (2026-11-01)

The example main.py now reads program_name from developer_settings for its window
caption and ICON_PATH from backend settings for its Tkinter icon. The window
still contains only the Example GUI label. Updated the README and existing real
GUI regression to verify the configured caption and actual icon assignment.
Validation: the real Tkinter GUI regression passed with the configured window caption and actual icon assignment. Ruff F and Git whitespace checks passed.


#### Provide GUI identity through environment variables (2026-11-01)

The watchdog now sets PROGRAM_NAME and ICON_PATH in the application's environment
from the project settings. main.py reads these variables for its Tkinter window,
removing its imports of backend settings. Direct runs without these variables
use Example GUI and Tkinter's default icon. Private PYAPP_* launcher protocol
remains stripped, and no identity metadata is added to application arguments.
Updated README, real GUI and real watchdog handoff coverage for the public values.
Validation: all four focused real GUI/watchdog integration tests passed, including environment identity propagation, normal GUI close and abrupt-exit handling. Ruff F and Git whitespace checks passed.


#### Restore PROGRAM_HAS_TERMINAL (2026-11-01)

Normal application launches now receive PROGRAM_HAS_TERMINAL="1" in classic
console/Windows Terminal modes and "0" in hidden mode, alongside PROGRAM_NAME
and ICON_PATH. The value describes the selected launch mode and is an environment
string, not a Python boolean or application argument. Added README usage and a
real watchdog/wrapper regression checking all three modes; terminal appearance
calls are stubbed so the test does not change the user's console.
Validation: all four watchdog integration tests passed, including real application environment checks for hidden, classic console and Windows Terminal modes. Ruff F and Git whitespace checks passed.

#### Safe Ruff/Pyrefly default cleanup in tracked source (2026-11-01)

Checked all 53 Git-tracked Python files, excluding generated environments and
ignored temporary files. The first pass reported 110 Ruff findings (104 E402,
five boolean comparisons and one ambiguous variable) and 18 Pyrefly errors.

- Kept the early entry-script handoff that catches dependency import failures.
  Added documented per-file E402 exceptions only where that bootstrap ordering
  is intentional. No global Ruff rule disabling or new Pyrefly ignores were added.
- Simplified boolean checks, preserved the explicit False case for optional close
  behavior, and renamed the ambiguous read_lines comprehension variable.
- Declared the watchdog protocol dictionary's heterogeneous value type and
  narrowed its binary stdout pipe to BufferedReader while preserving read1's
  responsive live-output behavior. Made process identity's non-None guard explicit.
- Initialized the package-lock local before its guarded read, avoiding an
  uninitialized-variable diagnostic without changing lock selection behavior.
- Imported re/threading before the wrapper's splitter classes can use them and
  ensured sys is available in the wrapper's outer exception handler. Kept the
  frontend wrapper compatible with Python 3.5 grammar.
- Added root pyrefly.toml with source/generated-file boundaries and the actual
  separate backend/application dependency paths. Missing rich/pipreqs reports are
  resolved by correct paths, not ignored. With dependency types resolved, guarded
  Rich traceback creation against sys.exc_info() returning None, which also fixes
  standalone diagnostic messages outside an active exception.
- Removed a redundant icon-scale float conversion and applied default Ruff
  formatting (46 files reformatted). Documented repeatable source-check commands.

Validation: Ruff default check and format check pass across all 53 source files.
Pyrefly default project checks report zero diagnostics (including warnings) with
both managed frontend Python 3.14 and backend Python 3.12 as interpreter targets;
24 pre-existing suppressed diagnostics remain. All 50 regression tests pass,
including native faults, logging/atexit, simultaneous launches, install rollback,
real GUI and compact shortcut checks. All 49 script modules import successfully.
The wrapper passes Python 3.5 syntax parsing; this is not a Python 3.5 runtime test.
Real Rich reporting passed with and without an active exception. Git whitespace
checks pass. Existing edits to the default package list and untracked Start.cmd
were preserved; no commits or pushes were made.

#### Replace icon-folder shortcuts with portable command launchers (2026-11-01)

Replaced code/backend/icons/regenerate icons.lnk with regenerate icons.cmd and
HOW_TO_CHANGE_ICONS.txt.lnk with HOW_TO_CHANGE_ICONS.cmd. Both resolve targets
from their own folder, report success/failure, wait for a keypress on either
outcome, and preserve the child's exit code. Icon generation runs in a separate
cmd process and suppresses inner acknowledgement prompts, matching root setup;
a plain exit in the child cannot close the outer reporting window. The help
launcher opens the instructions in Notepad and reports missing instructions as
exit code 2. Removed the two original binary shortcuts. The old regenerate link
still targeted B/miscellaneous; the new cmd uses batches/icons/regen_icons.bat.
Updated HOW_TO_CHANGE_ICONS.txt for cmd launchers, scripts/icons, the bundled
fallback location and the current placeholder-generation batch.

Validation: six disposable launcher fixtures passed in a relocated path with
spaces, an apostrophe and Unicode. Covered regeneration success (0), failure
(23), child-shell exit (17), viewer success, viewer failure and missing help (2).
Verified final prompt/status and preserved exit code in every case, plus the
inner-prompt suppression variable. Viewer tests used a stub instead of opening
Notepad. Actual ICO files were not regenerated or changed. Git whitespace checks
passed.


#### Restore developer launchers after the recent flattening moves (2026-11-01)

Added all 13 matching .bat entry points directly to code/backend/dev_tools and
removed their duplicate internal dispatch copies. They select the matching flat
DONT_CHANGE/scripts/dev_tools/*.py file and use the shared bootstrap runner,
forwarding arguments and exit status. Relative paths survive folder moves.

Root setup and icon regeneration now select their Python script directly and
invoke the shared runner from the protected outer command process. Removed the
redundant batches/generate_shortcuts.bat and batches/regen_icons.bat layers,
plus the unused install_embedded_python.bat shim (PowerShell bootstrap already
calls its .ps1 implementation directly). Kept the short B/*.bat shortcut targets
and shared ensure/run helpers, which still serve actual callers.

Updated DEV_TOOLS_FOR_PACKAGES_DIR so defaults and generated package reports use
the flattened public dev_tools folder. Preserved the maintainer's existing
DEFAULT_PYTHON_PACKAGES.txt and lock contents; updated the lock ignore path.
Fixed root setup references, icon action paths, and current tool documentation.
Removed stale README claims about deleted Git/verification/placeholder tools;
those intentionally moved tools were not restored into active code.

Added disposable dispatch regressions for every public batch, exact quoted/empty
argument forwarding, exit propagation, outer success/failure/plain-exit handling,
and static batch dispatch path existence. No package resets or ICO generation
are performed by these tests.
Validation: all 53 regressions passed, including the three new launcher/path
checks. All 40 remaining active script modules import, the actual backend
bootstrap succeeds, and default/package-report paths resolve to the public
folder. Ruff default lint and Pyrefly default passed; Git whitespace checks
passed. A full formatting check also noticed a concurrent, unrelated edit to
code/settings.py, which was left untouched. The maintainer's package-list/lock
contents and existing untracked pyrefly.toml were preserved. No production
package reset or icon regeneration was performed.

#### Instructions countdown and current-project review (2026-11-01)

OPEN_HOW_TO_CHANGE_ICONS.txt.cmd now starts Notepad asynchronously and, after
successful launch, prints 3, 2, 1 at one-second intervals before exiting 0.
The instructions can remain open after the console closes. Missing instructions
return 2; failed launch reports its exit status and retains the keypress prompt.
The independent root setup and icon regeneration acknowledgement policies were
not changed. The countdown uses built-in Windows PowerShell to work with both
interactive and redirected standard input.

Added a relocated-path regression with a stub viewer, actual timed countdown,
success/error/missing-document cases and preserved exit codes. All 54 regression
tests passed, including native crash and Tkinter coverage. The first sandboxed
full run hit access restrictions reading installed frontend package metadata in
the disposable pip fixture; the full unsandboxed run passed. No real package reset
or icon regeneration was performed. Git whitespace checks passed.

Saved reviews/2026-11-01-project-review.md and the standalone launch-flow.mmd.
The review compares historical environment exports (commit 6e80ab20) with the
current three public variables, identifies the five former metadata exports,
and explains that completion settings still work without being exported.
Includes concrete simplification/settings recommendations, gitignore exceptions
and lock policy, active WIP/stale settings/docs, deferred features and current
setup/start/stop/tools/help flow. Recommendations were not implemented as silent
settings removals. No commits or pushes were made.

#### Document all active Python modules and functions (2026-11-01)

Added or replaced placeholder docstrings throughout template-owned Python source.
All 44 modules now have module documentation; all 246 functions/methods (including
nested callbacks and stream adapters) and all 21 classes have docstrings.
Descriptions cover responsibilities, relevant return values, errors, locking,
logging, installer state, COM interfaces and completion behavior. Existing useful
docstrings and the frontend wrapper's Python 3.5 compatibility notes were retained.
Downloaded Python distributions, third-party packages and temporary artifacts were
excluded. Updated the example settings module description without changing values.

Verified documentation coverage with AST inspection and checked each generated
edit against its pre-edit AST after removing docstrings: executable statements
were unchanged. The wrapper still parses with Python 3.5 grammar. Ruff default
lint passes; Pyrefly reports zero errors (24 existing suppressed diagnostics).
All 54 regression tests pass, including native crash and Tkinter coverage; Git
whitespace checks pass. Existing unrelated edits were preserved. No commits or
pushes were made.

#### Remove unused installer parameter and restore public environment metadata (2026-11-01)

Removed check_auto_determine_flag_for_default_package_install from
ensure_python_distro: it was not read and no active source/helper caller passed
it. Retained install_default_packages(check_auto_determine_flag=...), which
still controls the requirements-file import-inference flag.

Restored five historical application environment exports in the watchdog child
environment: LOG_PATH, APP_ID, WDIR_IS_SCRIPT_DIR, CLOSE_AFTER_FAILURE and
CLOSE_AFTER_SUCCESS. Existing PROGRAM_NAME, ICON_PATH and PROGRAM_HAS_TERMINAL
remain. Boolean values use "1"/"0". LOG_PATH is the unique resolved log filename,
or empty when logging is disabled; APP_ID is empty when no identity is supplied.
WDIR_IS_SCRIPT_DIR describes the selected working-directory policy. Values
overwrite stale inherited metadata and are available in main.py through
os.environ. They are launch-time snapshots, not a communication channel for
changing watchdog settings. Private PYAPP_* protocol data stays filtered out.
Documented the eight public variables and boolean parsing in the root README.

Extended real watchdog integration coverage to check all eight values, logging
on/off, both directory policies, both completion booleans, nonempty taskbar ID
and overwriting stale inherited values. All 55 regressions pass, including native
crash and Tkinter coverage. Ruff default lint, Pyrefly default (zero errors;
24 existing suppressed diagnostics), and Git whitespace checks pass. No commits
or pushes were made.

#### Verify Rich traceback rendering and repair two blockers (2026-11-01)

Rich 15.0.0 rendering was exercised directly with serialized application errors.
Found an import blocker introduced when install_tests/install_tools were removed
from developer_settings.py: frontend_environment still imported those public
names, preventing process_exit from loading. Defined disabled internal
FRONTEND_INSTALL_TESTS/FRONTEND_INSTALL_TOOLS defaults in backend_settings and
wired both installer arguments and runtime-lock selection to them. Public
settings remain removed; CPython's own tests/legacy Tools remain disabled.

Found that rendering different application.py files in one process could reuse
linecache entries keyed by the relative filename, showing the previous file's
source context. Before rendering, process_exit now drops cached relative frame
names after selecting the traceback origin directory. It preserves relative
path display, source context and restoration of the previous working directory.

Added seven focused regressions in tests/test_rich_tracebacks.py: runtime error
source/metadata/frame trimming, explicit and implicit exception chains with
suppressed context, SyntaxError source/pointer, strict cp1252 output, plain-text
fallback after a Rich error, repeated filenames in different directories, and
launcher reporting with/without a currently handled exception. Test source paths
contain spaces, apostrophes and Unicode. Suppressed exception source can remain
visible as surrounding context; the suppressed exception itself is not rendered.

All 62 regressions pass, including native crash and Tkinter checks. Ruff default
lint, Pyrefly default (zero errors, 24 existing suppressed diagnostics), and Git
whitespace checks pass. Native terminal color/layout appearance was not manually
inspected in every terminal. Existing serialized application traceback limitations
remain: exception notes and nested ExceptionGroup details are not represented;
locals are intentionally hidden. No commits or pushes were made.

#### Remove redundant frontend installer constants (2026-11-01)

Removed FRONTEND_INSTALL_TESTS and FRONTEND_INSTALL_TOOLS and their imports.
Frontend runtime-lock selection records tests=False/tools=False directly, and
the installer explicitly receives install_tests=False/install_tools=False.
Behavior and existing lock compatibility remain unchanged: CPython's own tests
and legacy Tools are excluded without additional settings. Ruff default lint,
Pyrefly default (zero errors; 24 existing suppressed diagnostics), and Git
whitespace checks pass. No installation was run and no commits or pushes made.

#### Make the Rich traceback test runnable and add visible preview (2026-11-01)

The focused test_rich_tracebacks.py module previously only defined tests, so
running that file directly did nothing. Added its unittest.main entry point;
direct execution now prints the seven test results. The assertions intentionally
capture renderer output, so passing tests do not display each traceback example.

Added --preview to display a real production-rendered ZeroDivisionError with
nested application frames from a temporary source file. It prints to the terminal
without capture, cleans up its temporary fixture and leaves main.py unchanged.
Documented both commands in the Dev Helpers README. Verified direct execution
with the managed Python 3.14.6: all seven focused tests pass. The preview exits 0,
prints ZeroDivisionError and its source line, and does not enter the plain fallback.
No commits or pushes were made.

#### Audit clean-clone and new-app behavior (2026-11-01)

Saved reviews/2026-11-01-clean-clone-audit.md with confirmed tracked-input failure,
nonportable pip.exe/manual-terminal behavior, first-install package-lock/inference
bypasses, relaxed runtime-lock enforcement, worker/Tkinter callback exception
limits, obsolete shortcuts, naming edges and documentation/support gaps.
All 62 existing regressions pass; additional disposable/read-only probes reproduced
the findings. No production files, Git staging, commits or pushes were changed.
A complete online first setup on a clean Windows VM was not performed.

#### Document feature status and audit active settings/ignore rules (2026-11-01)

Replaced the root README's broad feature claims with 49 feature/status rows,
grouped by runtime/startup, shortcuts/icons, dependencies/tools and diagnostics/
process control. Explicitly distinguish implemented, partial and unimplemented
behavior. Documented first-install lock/inference limits, manual pip portability,
thread/GUI callback failure limits, naming/taskbar edges and missing automatic
cleanup/exception-note/group/cooperative-stop behavior. Removed missing Start.cmd
and included-benchmark claims, unsupported antivirus/licensing assurances, and
instructions to commit locks that the current rules ignore. Kept primary README
content focused on the source project without references to experiments or the
separate helper repository. Updated the internal README consistently.

Audited active Python references, including derived values within settings.
Removed the two unused backend paths CORRECT_START_SIGNAL_FILE_PATH and
DEV_TOOLS_REFERAL_NOTE_PATH. All 72 remaining backend-settings bindings and all
81 developer-settings bindings have active references. This does not assert
that every setting combination or partially implemented workflow is complete.
Clarified conditional instance prompting, global interpreter scope, unique-log
write/append behavior, version diagnostic files and the silent default Ctrl+C
sound. Replaced the stale pyproject.toml maintenance reminder in the INI.

Added targeted root/nested .gitignore maintenance reminders for layout bases,
shortcut output, temporary data, PID state, report outputs, tracked requirements
exceptions, locks and generated environments. Explained that ignored parent
folders cover their child manifests/helper files, while source/assets/inputs
remain tracked and Explorer visibility/import inference are separate concerns.
Added ignore patterns for frontend staging/previous/failed directories and
retained backend .previous directories. Matched Pyrefly exclusions to those
artifacts. Verified ten generated path cases and six tracked-input exceptions.

Found and corrected a leading space in crash.png's expected placeholder ID.
All ten shipped PNG identifiers were checked. Verified that the unchanged crash
placeholder now selects default_crash.png; ICO files were not regenerated.

During validation, the maintainer moved the four bootstrap files from
DONT_CHANGE/batches/bootstrap into DONT_CHANGE/scripts/setup. Updated all active
source batch/command callers and internal layout documentation for the move,
retaining compact B/*.bat shortcut targets. Updated nine helper batch callers and
two regression fixture modules without restoring the removed directory. The
initial regression run caught the stale dispatch paths; after repairs all 62
regressions pass, including native crashes, GUI and actual relocated batch tests.
Ruff default lint, Pyrefly default (zero errors, 24 existing suppressed diagnostics),
README local-link/stale-reference checks and Git whitespace checks pass. Existing
concurrent edits/staging were preserved. No commits or pushes were performed.

#### Confirm relocated bootstrap callers and optional Pyrefly (2026-11-01)

Verified that all active source launchers and developer helper callers now target
DONT_CHANGE/scripts/setup after the maintainer's bootstrap move. Eight focused
launcher/portable-path tests pass. The real relocated ensure_backend_python.bat
also succeeds against the healthy installed backend; no installation was needed.
Updated the wrapper diagnostic's obsolete Setup.cmd instruction to the actual
root setup filename.

Pyrefly and pyrefly.toml are optional development tooling, not setup/application
dependencies. Removed Pyrefly-specific maintenance reminders from backend settings
so they do not imply a runtime requirement. The local configuration was retained;
no tool was uninstalled. Existing concurrent edits/staging were preserved. No
commits or pushes were performed.

### 2026-11-01 - Follow-up to the clean-clone chat audit (#2, #4, #5, #7)

The maintainer confirmed the numbering from the chat beginning "Yes. I found several issues worth fixing before distributing a new app", rather than the separate detailed audit. A configured minor such as 3.14 must be required while accepting any 3.14.x patch.

- **#2 Portable manual package commands:** extracted `prepare_package_terminal` and run it after installation and healthy-runtime validation. It creates relative pip.cmd, pip3.cmd and versioned pip3.14.cmd adapters beside python.exe, ahead of Scripts on the package terminal PATH. They invoke the adjacent interpreter with `-E -s -m pip`, forward arguments and preserve exit status. The terminal/recovery instructions recommend `python -m pip`. Refreshed the current installed helpers and verified all three with --version. No packages were installed/reset. Direct third-party .exe launchers can still contain absolute interpreter paths.
- **#4 Worker/Tkinter errors:** the frontend wrapper retains the first uncaught threading exception (Python 3.8+), preserves the existing thread stderr hook, and detects errors retained by Tkinter's default callback handler. Final completion becomes failure without forcibly closing a GUI. A main-script exception takes precedence. Successful worker SystemExit and handled exceptions remain successful. Background traceback publication is atomic; the watchdog promotes a successful result to failure when non-daemon workers fail after main.py returns, including after sys.exit(0). Applications replacing hooks or using other event loops still own their reporting. Python 3.5 wrapper grammar remains valid.
- **#5 Required version components:** a healthy runtime must match every configured component. 3.14 accepts any 3.14.x; 3.14.6 requires that patch. Keeping a mismatching environment now cancels this launch instead of bypassing the version setting. Incompatible resolved runtime-lock entries are ignored and the actual newly installed version is validated before recording success. The lock can select an exact compatible rebuild download without imposing a patch on a minor-only setting.
- **#7 App-name edge cases:** shortcut filenames reserve room for .lnk, count the Windows component limit in UTF-16 units, truncate safely and hash long names to distinguish action suffixes. Filename sanitation handles reserved device names with extensions/trailing spaces. Non-Latin names get a stable nonempty taskbar ID; long IDs use a stable digest. Custom shortcut actions that sanitize to the same filename fail before writing. Kept compact B targets. Updated the external startup benchmark to use the same filename/identity helpers. Full Windows path-length limits still apply.
- **Documentation:** updated feature status, version semantics, background-error boundaries and portable pip behavior. No active source documentation refers to Start.cmd. Expanded logging advice: disable `enable_log_for_Windows_terminal_start` for a real TTY; launch metadata plus stream isatty detects redirection, not incompatibility. No blanket warning or pseudoconsole implementation was added.
- **#3 remains a proposed fix:** first runtime installation/default runtime replacement still calls install_packages_from_file directly. It skips the package-lock reader and default import-inference flag, then writes healthy package state. A subsequent healthy launch therefore does not repair the policy bypass. Recommended change: route only the declared-default branch through install_default_packages(check_auto_determine_flag=True, ...), preserving the explicit empty/current/pinned/inferred migration branches. Add fresh-install tests for a matching saved lock and enabled inference before making that change. The maintainer asked for explanation/how to fix this item, so it was not silently changed.

Validation: 73 tests verified (72 passed in full discovery and the opt-in native-crash test passed separately). Includes 11 new tests in tests/test_application_fixes.py for relocation/argument/exit handling, minor/exact version rules, stale locks, Unicode/long names, colliding actions, joined/late/handled worker errors, Tkinter callbacks and main-error precedence. Ruff defaults pass for active project code and changed helper/test files. Frontend wrapper parses with Python 3.5 grammar. Current pip/pip3/pip3.14 adapters all return installed pip successfully. Optional Pyrefly was attempted, but its former project config is absent; auto configuration scans generated dependencies and cannot resolve the code import root, so that output is not a meaningful project type-check result.

### 2026-11-01 - Markdown READMEs and package-maintenance guidance

- Converted the two project-owned README.txt files to README.md: code/backend (previously empty, now an application/backend orientation guide) and code/backend/dev_tools (rewritten with Markdown headings, all 13 commands and practical workflows). Other managed READMEs in the template and Dev Helpers were already Markdown. Third-party README/license files inside generated runtimes/packages were preserved; plain-text icon instructions are not README files.
- Updated the root README package-guide link and the active Dev Helpers TODO reference to the renamed guide. Added prominent guidance to use code/backend/dev_tools for managed package changes.
- Documented explicit-default edits plus reset, interactive pip usage through open_package_terminal, exit for validation/state recording, and saving installed packages as committed defaults. Explained the defaults-file inference flag, managed/global separation, live manual edits versus staging, and the risk of stale state when modifying packages outside the tools.
- Added a source-verified explanation of Python/runtime probes, required version components, backend pins/imports, package manifests, nested requirements fingerprints, metadata hashes, RECORD payload existence and installation-time pip check. Explicitly documented that startup does not import-test every dependency or hash all payload contents.
- Corrected the root taskbar feature-status row to reflect the already implemented non-Latin/long-name handling.

Validation: all relative Markdown links in the four project READMEs resolve. No project-owned README.txt files or active primary-project links to them remain. This pass changes documentation only; no packages, application behavior or inference settings were changed. Proposed simplifications are advice, not implemented changes.

### 2026-11-01 - Powerful portable application package console

Replaced the raw CMD package prompt with an interactive package-command console in the existing scripts/dev_tools/open_package_terminal.py. Kept all 13 public batches; no additional forwarding Python entry script was retained.

- Package shorthand accepts one name, space-separated names, comma-separated names and Python-style lists of strings. Versions/ranges, extras, URLs, quoted requirements paths and install -r are forwarded as literal arguments. Windows CommandLineToArgvW parsing avoids shell interpretation of >, &, pipes or command chaining; Python lists use ast.literal_eval and require strings. Valid commas inside requirement ranges/extras are preserved.
- Automatic commands honor use_uv_to_install_packages. They prefer uv when enabled and retry with pip if uv is absent, cannot start or returns failure. Explicit pip commands force pip; explicit uv pip commands force uv and preserve uv failure. uv --version/help work too. This is an app-package console, not a uv project/environment manager.
- uv is resolved at use time from the managed backend module or an available uv.exe, avoiding recursion through uv.cmd. If missing it attempts the same pinned optional uv version used by package_tools, once per session, in backend Python's local site-packages. Extracted the existing 0.8.22 pin to shared UV_VERSION; no pin upgrade was made. Automatic commands remain usable with pip if provisioning fails.
- Commands include install, upgrade, uninstall/remove, list/outdated, show, check and freeze, plus help/status/save/exit. Common verbosity/cache flags are supported; advanced flags can be passed after the package action. The console supplies the managed interpreter/package target. Interpreter/target overrides and unsupported global option layouts are rejected rather than accidentally changing another environment. uv check/tree use interpreter discovery because those commands do not support --target.
- Errors and Ctrl+C keep the interactive prompt open. Status shows resolved paths, configured installer and last exit code. Installed state is validated on exit. Explicit save validates packages, saves installed versions as defaults with inference disabled, then refreshes the changed requirements fingerprint. It does not implicitly change defaults after every install. Live mutations remain live; transactional resets are still available separately.
- Generated pip/pip3/versioned pip/uv .cmd adapters and the legacy generated terminal batch now resolve the shared backend runner and existing console module relative to themselves. They forward arguments and preserve exit status after moving the folder. Refreshed the existing generated adapters. The public batch also accepts a one-shot command.
- Updated missing-package recovery to open the same console. Its child owns the environment lock, running-instance check and final validation. Removed the parent-held lock and redundant nested forwarding function that would otherwise deadlock with the newly locking child. Updated recovery wording so users need no python -m invocation in managed mode.
- Updated the root README, backend internals and package guide with examples, preference/fallback behavior, explicit-tool semantics, save behavior, limits and portability details. No packages were installed into or removed from the real application's package directory during verification; offline install/uninstall tests used disposable targets.

Validation: the full 82-test suite passed, including native crash, Tkinter, batch dispatch and offline pip/uv integration. A final focused 10-test console run passed after adding the interpreter-override guard (83 distinct regressions in the current suite). Real public interactive batch smoke test exercised pip --version, uv --version, list, check and exit with successful dependency/state validation. Real portable pip/uv adapters returned version information successfully. Relocated adapter fixtures cover spaces/apostrophes/Unicode, arguments and nonzero exit preservation. Ruff defaults pass for changed source. All updated README links resolve. No commit/push was performed.

### 2026-11-01 - Centralize the optional uv version

Moved UV_VERSION = "0.8.22" from scripts/package_tools.py into settings/backend_settings.py. Both the shared installer and interactive package console now import the setting directly from backend_settings. The version and installer behavior are unchanged. Ruff passed for all three edited modules; the focused uv provisioning/fallback regression passed.

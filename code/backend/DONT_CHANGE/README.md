# PyApp-Template backend internals

This folder holds the Windows launcher around `code/main.py`: the uv bootstrap, the
environment management, logging, process tracking and completion handling. Application
authors normally edit only `main.py`, `settings.py` and `backend/developer_settings.py`.

## Layout

```text
DONT_CHANGE/
  B/              Short shortcut targets: W (terminal), N (no terminal), Q (stop),
                  S (settings), M (main.py), L (logs), C (crash logs)
  backend_settings.py  internal paths and constants
  data/           import_to_package.txt (import name -> PyPI name, for the import finder)
  bootstrap/      run.bat, ensure_runtime.bat (fast path), resolve_runtime.ps1 (uv + Python),
                  open_folder.bat / open_file.bat (open shortcuts without Python)
  actions/        start_program, stop_program, open_folder / open_file (fallbacks of the
                  open shortcuts) and gen_icons. Plain modules with a main(); every tool
                  runs as `entrypoint.py <tool.py> [args]` (see bootstrap/run.bat)
  runtime/        background_watchdog, script_wrapper, process_exit, _pyapp (protocol),
                  send_ctrl_c (Stop for console apps)
  setup/          generate_shortcuts (Setup)
  scripts/
    config.py     settings loading and validation
    errors.py     SettingsError / SetupError / LaunchCancelled (shown without a traceback)
    entrypoint.py runs every tool with one error, exit-code and "Press Enter" policy
    com_tools.py  minimal Windows COM helpers (taskbar identity of shortcuts and consoles)
    uv_env.py     uv, Python selection, generated pyproject.toml, uv.lock/.venv management
    dev_tools.py  all dev tools (backend/dev_tools/*.cmd call it)
    diagnostics.py  records errors that are ignored on purpose (tmp/diagnostics.log)
    ...           focused helpers (console, filesystem, instance policy, window focus,
                  import finder, traceback rendering, process registry)
  icon_related/   shipped placeholder icons and instructions
  tmp/            runtime cache, environment stamp, locks, running-instance records,
                  per-run folders and diagnostics.log (ignored by Git)
```

## Startup

1. A shortcut runs `B/W.bat` or `B/N.bat`, which call `bootstrap/run.bat`.
2. `ensure_runtime.bat` loads `tmp/runtime.cmd` (uv and launcher-Python paths) while its stamp
   matches: this folder's path (a copied project never uses the original's uv/Python), the
   SHA-256 of `developer_settings.py` and the time/size of `backend/.python-version`, and both
   executables still exist. Otherwise `resolve_runtime.ps1` reads the `[bootstrap]` settings
   (unindented one-line literals; like Python, the last definition wins), finds or installs uv
   according to `uv_prefer` / `uv_install_if_missing` / `uv_version`, finds or installs the
   project's Python with uv (`backend/.python-version`, else `python_version`), checks the 3.8
   minimum and writes the cache. The cache is UTF-8; it is read with code page 65001 unless its
   first line is `rem ascii`, so non-ASCII project paths work and ASCII ones skip `chcp`.
3. `run.bat` starts `python -I -S -X utf8 scripts/entrypoint.py <tool.py> [args]`: isolated,
   no `site`, standard library only. `entrypoint.py` puts the code folder on `sys.path` and runs
   the tool's `main()`. Settings are read with `config.settings()` when needed, never at import
   time, so a mistake in `developer_settings.py` is reported, not a traceback.
4. `start_program.py` validates the settings, applies `instance_policy`, sets the console's
   title/icon/taskbar group, hides tool folders in Explorer, prunes old logs and calls
   `uv_env.ensure_environment()`:
   - writes `backend/.python-version` on the first run;
   - offers the migration menu when `python_version` differs from `.python-version`;
   - generates `backend/pyproject.toml` from `packages` and the project's Python
     (`requires-python = "==X.Y.*"`); its header records the list it was generated from, so a
     change made to the file (e.g. `uv add`) is copied into `packages` instead of being lost;
   - **fast path:** when `tmp/environment.ok` matches a fingerprint of everything the check
     depends on (project folder, interpreter, uv, `pyproject.toml`, `uv.lock`,
     `.python-version`, the venv's `pyvenv.cfg`, `python.exe` and `site-packages` folder), the
     steps below are skipped;
   - `uv lock` when `pyproject.toml` changed (offline first);
   - re-links `backend/.venv` to the project's Python when the project moved
     (`uv venv --allow-existing`, keeps all packages, works offline); rebuilds it beside the
     old one when the Python minor version changed;
   - `uv sync --locked --inexact` (offline first), then writes the new stamp.
5. The watchdog registers the run, starts `script_wrapper.py` in the app interpreter,
   captures output, waits, and hands the outcome to `process_exit.py`.

`uv_env.uv_environment()` mirrors `Set-UvEnvironment` in `resolve_runtime.ps1`; keep both
in sync when changing how uv is configured. Lookups run from the system temp folder,
because uv would otherwise discover `backend/.venv` as "the" Python. Project commands run with
the backend folder as working directory (the uv project). Project commands use the
"prefer managed" Python preference because uv caches interpreter details that are stale
right after a re-link.

## Open shortcuts

Setup passes each "open" shortcut its target: the log and crash-log folders (created by Setup)
and the files `main.py` and the user settings file. `B/L.bat`, `C.bat`, `M.bat` and `S.bat`
open them through `bootstrap/open_folder.bat` / `open_file.bat` without starting Python
(VS Code via its `Code.exe`, else Notepad). Only when no target was passed (a log path
relative to the start folder, or with date codes in its folder part) or the file is missing do
they run `actions/open_folder.py` or `actions/open_file.py`. Setup records the targets in
`backend/shortcuts_created_by_setup.json`; each start warns when the settings no longer match
them (run Setup again).

## Runtime protocol

`runtime/_pyapp.py` (standard library, Python 3.8+) is also imported inside the app
interpreter, as the top-level module `_pyapp`: a name that cannot shadow the app's own
modules. It defines the wrapper exit codes (`WrapperExit`), the watchdog outcomes
(`ExitMode`, deliberately different numbers), the explicit mapping between them
(`EXIT_MODE_FOR_WRAPPER_EXIT`) and the traceback report. The wrapper strips its own and
`runpy`'s frames, so reports look like `python main.py`; it stores CPython's own formatting
(`plain`, used for exception groups) and a structured chain with source context for the app's
own frames. `traceback_render.py` turns the report into plain text (crash logs) or ANSI colors
(terminal).

Each run owns `tmp/runs/<id>/` with its wrapper config, readiness, startup
acknowledgement, result and traceback files, and `stop-requested` when it was stopped.

## Process control

`runtime_state.ProcessRegistry` keeps one verified identity record per running watchdog in
`tmp/running/` (PID, creation time, executable, console window, app child, run folder).
Stop (and `instance_policy = "replace"`) first asks each instance to close: `WM_CLOSE` to the
app's windows, or Ctrl+C to its console (sent by `runtime/send_ctrl_c.py`, a detached helper)
for a console app. It writes `stop-requested` into the run folder, so the watchdog ends
without sounds, menus or prompts. After `stop_timeout_seconds`, instances that still run are
terminated with their process trees through the Win32 API (Toolhelp snapshot +
`TerminateProcess`), deliberately without `taskkill`/WMI.

Each project copy has its own taskbar identity (AppUserModelID = program name + hash of
program name and project folder, `setup/generate_shortcuts.project_app_id`). Setup stores it in
the shortcuts; the launcher sets it on its console windows and the app's process. The registry lock is not held while
waiting, because an ending watchdog needs it to unregister. `instance_policy.py` shows its
dialogs without holding the lock; `windows_focus.py` finds and activates the running
instance's window.

## Errors

- `scripts/errors.py`: problems the user can fix. `entrypoint.py` prints them (and any error
  raised while running `developer_settings.py`, with its line number) without a traceback.
- `scripts/diagnostics.py`: cosmetic steps (window icon, title, colors, focus, ...) must not
  stop the app, so their errors are ignored, but each one is appended to
  `tmp/diagnostics.log` (the `status` dev tool shows the count; `PYAPP_DEBUG=1` also prints
  them).

## Compatibility rules

- Python files under `scripts/`, `actions/`, `runtime/` and `setup/` must run on Python 3.8+ with the standard library only:
  use `from __future__ import annotations`, no `match`, no parenthesized `with`, no
  `str.removeprefix`, no `typing.override`, guard `sys.stdlib_module_names`.
- Folder locations are mirrored in `backend_settings.py`, the bootstrap batch/PowerShell
  files and the root `.gitignore`; change them together.

## Licensing

Template files here are `MIT OR Apache-2.0`; `data/import_to_package.txt` is derived from
pipreqs (Apache-2.0). See [LICENSE.md](LICENSE.md).

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
  bootstrap/      run.bat, ensure_runtime.bat (fast path), resolve_runtime.ps1 (uv + Python)
  actions/        start_program, stop_program, open_* and icon generation
  runtime/        watchdog, script_wrapper, process_exit, protocol
  setup/          generate_shortcuts (Setup)
  scripts/
    config.py     settings loading and validation
    uv_env.py     uv, Python selection, pyproject/uv.lock/.venv management
    dev_tools.py  all dev tools (backend/dev_tools/*.cmd call it)
    ...           focused helpers (console, filesystem, instance policy, window focus,
                  import finder, traceback rendering, process registry)
  icon_related/   shipped placeholder icons and instructions
  tmp/      runtime cache, locks and per-run diagnostics (ignored)
```

## Startup

1. A shortcut runs `B/W.bat` or `B/N.bat`, which call `bootstrap/run.bat`.
2. `ensure_runtime.bat` loads `tmp/runtime.cmd` (uv and launcher-Python paths) when
   `developer_settings.py` and `code/.python-version` are unchanged and both files exist.
   Otherwise `resolve_runtime.ps1` reads the `[bootstrap]` settings, finds or installs uv
   according to `uv_prefer` / `uv_install_if_missing` / `uv_version`, finds or installs the
   project's Python with uv (`code/.python-version`, else `python_version`), checks the 3.8
   minimum and writes the cache. The cache is UTF-8 and read with code page 65001, so
   non-ASCII project paths work.
3. The entry script runs as `python -I -S -X utf8`: isolated, no `site`, standard library only.
4. `start_program.py` validates the settings, applies `instance_policy`, prunes old logs and
   calls `uv_env.ensure_environment()`:
   - writes `code/.python-version` and `requires-python = "==X.Y.*"` on the first run;
   - offers the migration menu when `python_version` differs from `.python-version`;
   - `uv lock` when `pyproject.toml` changed (offline first);
   - re-links `code/.venv` to the project's Python when the project moved
     (`uv venv --allow-existing`, keeps all packages, works offline); rebuilds it beside the
     old one when the Python minor version changed;
   - `uv sync --locked --inexact` (offline first) on every start.
5. The watchdog registers the run, starts `script_wrapper.py` in the app interpreter,
   captures output, waits, and hands the outcome to `process_exit.py`.

`uv_env.uv_environment()` mirrors `Set-UvEnvironment` in `resolve_runtime.ps1`; keep both
in sync when changing how uv is configured. Lookups run from the system temp folder,
because uv would otherwise discover `code/.venv` as "the" Python. Project commands use the
"prefer managed" Python preference because uv caches interpreter details that are stale
right after a re-link.

## Runtime protocol

`runtime/protocol.py` (standard library, Python 3.8+, also imported inside the app
interpreter) defines the wrapper exit codes (`WrapperExit`), the watchdog outcomes
(`ExitMode`) and the traceback report. The wrapper strips its own and `runpy`'s frames, so
reports look like `python main.py`; it stores CPython's own formatting (`plain`, used for
exception groups) and a structured chain with source context for the app's own frames.
`traceback_render.py` turns the report into plain text (crash logs) or ANSI colors (terminal).

Each run owns `tmp/runs/<id>/` with its wrapper config, readiness, startup
acknowledgement, result and traceback files.

## Process control

`runtime_state.ProcessRegistry` keeps one verified identity record per running watchdog
(PID, creation time, executable, console window, app child). Stop terminates verified
process trees with the Win32 API (Toolhelp snapshot + `TerminateProcess`), deliberately
without `taskkill`/WMI. `instance_policy.py` shows its dialogs without holding the registry
lock; `windows_focus.py` finds and activates the running instance's window.

## Compatibility rules

- Python files under `scripts/`, `actions/`, `runtime/` and `setup/` must run on Python 3.8+ with the standard library only:
  use `from __future__ import annotations`, no `match`, no parenthesized `with`, no
  `str.removeprefix`, no `typing.override`, guard `sys.stdlib_module_names`.
- Folder locations are mirrored in `backend_settings.py`, the bootstrap batch/PowerShell
  files and the root `.gitignore`; change them together.

## Licensing

Template files here are `MIT OR Apache-2.0`; `data/import_to_package.txt` is derived from
pipreqs (Apache-2.0). See [LICENSE.md](LICENSE.md).

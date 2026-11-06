# 🐍 PyApp-Template

Turn a Python script or Tkinter app into a Windows application that users start from a
shortcut. The template uses [uv](https://docs.astral.sh/uv/) to provide Python and the
app's packages, adds logging, readable crash reports, completion actions and process
control, and can make the whole folder portable for offline use. Users do not need
Python installed.

Start with the GUI example in `code/main.py`, then replace it with your own code.

---

## Quick start

1. Clone/download/copy this repository.
2. Optional: change `program_name`, `python_version` and the other settings in
   `code/backend/developer_settings.py`.
3. Run **`Setup - run first and after moving folder.cmd`**. It finds or installs uv,
   installs Python, creates the app environment and creates the shortcuts (project
   folder and Start Menu).
4. Start the app with the generated shortcut. Edit `code/main.py`; list the packages it
   needs in `packages` in `developer_settings.py` (or use `dev_tools/add_packages.cmd`).
5. Commit `code/backend/uv.lock` and `code/backend/.python-version` with your app; they are
   created on the first run and pin the exact Python and package versions.

Run Setup again after moving or renaming the project folder: it refreshes the shortcuts.
Each copy of the project gets its own taskbar group, so two copies (or two apps made from
this template) never mix their windows or pinned shortcuts. After a move, pin the new
shortcut again.
The Python environment itself adapts to a new location automatically.

---

## How it works

```text
shortcut ─▶ B\W.bat / B\N.bat ─▶ bootstrap\ensure_runtime.bat
                                   │  fast path: cached uv + Python paths (no PowerShell)
                                   └▶ resolve_runtime.ps1 (only when settings changed or files moved):
                                      find/install uv, find/install Python with uv
           ─▶ start_program.py  (runs on the project's Python with -I -S: standard library only)
                │  validates settings, applies instance_policy, generates pyproject.toml from
                │  developer_settings.py, keeps uv.lock and backend\.venv in sync (uv lock / uv sync;
                │  skipped while nothing changed since the last successful start)
                └▶ background_watchdog.py ─▶ script_wrapper.py ─▶ code\main.py (in backend\.venv)
                                          └▶ process_exit.py (sounds, crash log, recovery menu)
```

### Python versions

`python_version` accepts `""` (newest stable, chosen once and kept), `"3"`, `"3.14"`,
`"3.14.6"`, `"3.14t"` (free-threaded) and any other request string uv understands.

**Supported are all Python versions the installed uv can provide — currently CPython
3.8.2 and newer on Windows x64.**

Changing `python_version` later is safe: the next launch (or the `change_python` dev
tool) shows a menu to switch and re-lock (keeping versions), switch and upgrade, switch
with an empty dependency list, keep the current Python for now, or write the current
version back into the settings. The new environment is built next to the old one and
only swapped in when it works; on failure everything is restored.

### Where uv, Python and the packages come from

| Setting | Options |
| --- | --- |
| `python_source` | `"local"` (uv installs Python into `code/backend/pythons`, portable), `"uv_user"` (uv's per-user folder, shared by projects), `"system_if_matching_else_local"` (an installed Python matching `python_version`, else local), `"system_default_any_version"` (the default installed Python, any version; falls back to a local install if there is none) |
| `package_environment` | `"project_venv"` (uv-managed `code/backend/.venv`, recommended) or `"interpreter_site_packages"` (the selected system interpreter's own packages; the launcher installs nothing there unless `allow_installing_into_global_python = True`) |
| `uv_prefer` | `"global"` or `"local"`: which uv to use when both exist |
| `uv_install_if_missing` | `"global"` (Astral's installer, adds uv to your user PATH), `"local"` (download into `code/backend/uv`, verified against the published SHA-256) or `"never"` |
| `uv_version` | `""` (latest), an exact version (`"0.11.32"`) or a range (`">=0.9,<1"`). A global uv outside the range is left untouched and a local uv is installed instead. |
| `uv_user_python_visible_globally` | for `"uv_user"`: register the Python with the `py` launcher and put it on PATH |
| `uv_cache` | `"global"` (uv's per-user cache) or `"local"` (`code/backend/uv-cache`) |
| `allow_downloads_at_launch` | `False` makes normal launches fail with a clear message instead of downloading (Setup and dev tools may always download) |
| `use_system_certificates` | use the Windows certificate store (some company proxies need this) |

Settings marked `[bootstrap]` in `developer_settings.py` are read before any Python
exists; keep them on one line as plain values. All settings are validated before a
launch, and mistakes are reported with the setting name and the allowed values.

---

## Dependencies and dev tools

The app's packages are the `packages` list in `developer_settings.py`, e.g.
`packages = ["requests", "numpy>=2"]`. That is the only place to edit them. The exact
versions are locked in `code/backend/uv.lock` (with hashes); the launcher checks the
environment with an offline `uv sync` on every start (fast when nothing changed).

uv itself needs a `pyproject.toml`: the launcher generates `code/backend/pyproject.toml`
from `packages` and `python_version` (ignored by Git, do not edit it). If it is changed
anyway, e.g. with `uv add` in the package terminal, the change is copied back into
`packages` on the next start or dev tool run; if both were changed, `developer_settings.py` wins.

The tools in `code/backend/dev_tools` (or `Dev Menu.cmd` for all of them) edit `packages` for you:

| Tool | Purpose |
| --- | --- |
| `add_packages.cmd` / `remove_packages.cmd` | add or remove packages (`uv add` / `uv remove`, recorded in `packages`) |
| `upgrade_packages.cmd` | upgrade all (or the named) packages within their limits |
| `sync_packages.cmd` | make the environment match `uv.lock` exactly |
| `find_imports.cmd` | find the packages your code imports (offline), review them, add the missing ones |
| `package_terminal.cmd` | command prompt with the environment activated and uv on PATH |
| `change_python.cmd` / `update_python.cmd` | switch Python version / newest patch (and newest minor for `python_version = ""`) |
| `make_portable.cmd` | put uv, Python and all packages into this folder and switch the settings to them (asks first) |
| `export_requirements.cmd` | write `code/backend/requirements.txt` from `uv.lock` |
| `status.cmd` | show uv, Python, environment, lock and shortcut state and errors the launcher ignored |
| `clean.cmd` | delete logs, crash logs or per-run diagnostics |
| `remove_shortcuts.cmd` | remove every shortcut Setup created (project folder, Start Menu, Desktop) |

See [code/backend/dev_tools/README.md](code/backend/dev_tools/README.md) for details.

### Portable/offline distribution

Run `make_portable.cmd` and accept the settings it shows (`uv_prefer`/`uv_install_if_missing`
= `"local"`, `python_source = "local"`, `package_environment = "project_venv"`), optionally
set `allow_downloads_at_launch = False`, and copy the whole folder. On another PC or in
another location the environment is re-linked to the copied Python automatically
(no download, no reinstall); run Setup there to create shortcuts.

---

## Shortcuts and instances

Setup creates the enabled shortcuts in the project folder, a Start Menu folder
(`start_menu_shortcuts`) and optionally on the Desktop (`desktop_shortcuts`, e.g.
`["no_terminal"]`). It remembers what it created (`code/backend/shortcuts_created_by_setup.json`)
and removes shortcuts that are no longer wanted, e.g. after renaming one. Shortcuts of
other copies of the project are never removed. Existing shortcuts are replaced only by a
complete new one.

The Logs, Crash Logs, Settings and Edit-main.py shortcuts open their folder or file directly,
without starting Python (main.py and the settings file open in VS Code if installed, else
Notepad). They store the location Setup resolved, so run Setup again after changing
`log_path`, `crash_log_path` or `user_settings_path`; each start reminds you if they differ.

`instance_policy` decides what happens when the app is started while it already runs:
`"allow"`, `"focus"` (bring the running window to the front; asks to replace an instance
without a window), `"prevent"`, `"replace"` or `"ask"`.

The Stop shortcut (and replacing an instance) first asks the app to close, like clicking
its window's X (a console app gets Ctrl+C), so it can save its work, and then waits up to
`stop_timeout_seconds`. Whatever still runs after that is terminated with its process tree
(Win32 API, no WMI/taskkill, so it also works where those are broken). A stopped run ends
without completion sounds, menus or prompts.

---

## Logs, crash reports and tracebacks

Each run gets unique log names. The normal UTF-8 log contains your prints and inputs with
optional time prefixes; the `.output.log` companion captures raw output including native
and child-process output. Logging turns stdout/stderr into pipes, so disable terminal
logging (`enable_log_for_terminal_start`) if your app needs a real console.
Old logs and run diagnostics are pruned (`max_log_files` counts runs: a log and its
`.output.log` are kept or deleted together; `max_run_folder_age_days`).

Crash reports and terminal tracebacks look exactly like running `python main.py`
(launcher frames are removed), including exception chains, notes and exception groups,
plus `traceback_extra_lines` lines of context around your own code and optional colors.

A missing module offers: add the package to the project, install it without recording,
find all imports of the project and add the missing ones, or open a package terminal; the
app then restarts. If the missing import is one of your own modules, it says so instead.

Mistakes in `developer_settings.py` (wrong values, typos such as `Ture`, syntax errors) are
reported with the setting name or line number instead of a traceback. Errors of cosmetic
launcher steps (window icon, colors, focus, ...) never stop the app; they are recorded in
`code/backend/DONT_CHANGE/tmp/diagnostics.log` (see `status.cmd`).

---

## Project structure

```text
.
├── Setup - run first and after moving folder.cmd
├── code/
│   ├── main.py                 <<< YOUR APP
│   ├── settings.py             <<< OPTIONAL END-USER SETTINGS
│   └── backend/
│       ├── developer_settings.py   <<< APP / PYTHON / PACKAGE / UV SETTINGS
│       ├── uv.lock, .python-version  exact package and Python versions (generated, commit)
│       ├── pyproject.toml      generated from developer_settings.py (ignored)
│       ├── .venv/              app environment (generated, ignored)
│       ├── dev_tools/          package and Python tools
│       ├── icons/              icon sources and regeneration
│       ├── pythons/, uv/       local Python/uv when installed locally (ignored)
│       └── DONT_CHANGE/        launcher internals (see its README)
├── logs/                       program logs
└── crash logs/                 crash reports
```
## Licensing

The template-owned files in `code/backend/DONT_CHANGE` are available under `MIT OR Apache-2.0`
(the import-name mapping is derived from pipreqs, Apache-2.0). uv, Python distributions and
third-party packages keep their own licenses. Projects created from this template must replace
the project-license placeholder in [`LICENSE.md`](LICENSE.md).

This repository was originally built by Florian Lindinger: https://github.com/FlorianLindinger/PyApp-Template

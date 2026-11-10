# Dev tools

Double-click a tool, or run it from a terminal with arguments (e.g. `add_packages.cmd requests "numpy>=2"`; quote requirements with `<`, `>` or `|`, which the command prompt would otherwise treat as redirection).
`Dev Menu.cmd` lists all of them. The **&lt;name&gt; - Tools** shortcut offers the people using the app the few they may need (status, repair, add packages, package terminal, make self-contained, clean, remove shortcuts), each with a note on what it changes; set `tools_shortcut_name = None` to leave it out. Every tool validates `developer_settings.py` first and
prepares the environment if needed. Close running app instances before changing packages
or Python — Windows locks the files they use.

| Tool | What it does |
| --- | --- |
| `add_packages.cmd [names]` | `uv add`: resolves and installs the packages, adds them to `packages` in `developer_settings.py` and updates `pyapp/generated/uv.lock`. Asks for names when none are given. |
| `remove_packages.cmd [names]` | `uv remove`: lists `packages` and removes the chosen ones. |
| `upgrade_packages.cmd [names]` | `uv lock --upgrade` (or `--upgrade-package` for the named ones), then an exact sync. Test the app and commit `uv.lock`. |
| `sync_packages.cmd` | Makes `pyapp/generated/.venv` match `uv.lock` exactly; removes packages installed by hand. |
| `find_imports.cmd` | Offline import finder: scans the code folder (not `pyapp/`), drops the standard library and your own modules, maps imports to packages (installed metadata first, then `DONT_CHANGE/data/import_to_package.txt`, else the import name — marked "guess"). Optional imports start unchecked: imports inside `try/except ImportError`, or inside a broad `except`/`except Exception` whose `try` block only imports. Review, then the checked ones are added with `uv add` (and recorded in `packages`). |
| `package_terminal.cmd` | Command prompt in `code/` with the environment activated and uv on PATH: `uv add`, `uv pip list`, `python ...` (uv commands use the project in `pyapp/generated/`; `uv add`/`uv remove` are copied into `packages` on the next start). `uv pip install NAME` installs without recording (the next exact sync removes it). |
| `change_python.cmd [version]` | Writes a new `python_version` into the settings and runs the migration menu (re-lock keeping versions / upgrade / empty package list / keep / write back). |
| `update_python.cmd` | Installs the newest patch release of the project's Python and rebuilds the environment if needed. With `python_version = ""` it also offers a newer minor version. System Pythons are updated with their own installers. |
| `make_self_contained.cmd` | Makes the folder run on other PCs without internet or installing anything. First explains what it does and shows the settings it will change (`python_source`, `uv_prefer`, `uv_install_if_missing` → local) and asks; then copies uv into `pyapp/generated/uv`, installs the project's Python into `pyapp/generated/pythons`, rebuilds the environment on it and applies those settings. Declining changes nothing. `status.cmd` shows whether the project is self-contained. |
| `export_requirements.cmd` | Writes `pyapp/requirements.txt` (pinned, without hashes) from `uv.lock` for tools that need that format. |
| `status.cmd` | Settings validity, uv (version, local/global), launcher Python, `.python-version`, `requires-python`, `packages` (and whether `pyproject.toml` matches), environment base/relocatability, lock state, shortcuts, and errors the launcher ignored on purpose (`DONT_CHANGE/tmp/diagnostics.log`). Works without uv. |
| `clean.cmd` | Deletes logs, crash logs or per-run diagnostics. |
| `remove_shortcuts.cmd` | Removes every shortcut Setup created (project folder, Start Menu, Desktop). Run Setup to create them again. |

## Typical workflows

- **New dependency:** add it to `packages` in `developer_settings.py` and start the app, or `add_packages.cmd requests` → test → commit `developer_settings.py` and `pyapp/generated/uv.lock`.
- **Existing code with imports:** `find_imports.cmd` → review → add.
- **New Python version:** `change_python.cmd 3.13` → option 1 → test → commit `developer_settings.py`, `pyapp/generated/.python-version` and `pyapp/generated/uv.lock`.
- **Hand over a folder that runs offline on another PC:** `make_self_contained.cmd` → accept → copy the whole folder, e.g. as a zip (a Git clone lacks the local uv, Python and packages, which Git ignores) → on the other PC, run `Setup - run first and after moving folder.cmd` once for the shortcuts.
- **Move the folder on the same PC:** just move it, then run `Setup - run first and after moving folder.cmd` for the shortcuts. The environment adapts by itself; nothing is downloaded.

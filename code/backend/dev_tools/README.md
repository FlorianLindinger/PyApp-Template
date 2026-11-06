# Dev tools

Double-click a tool, or run it from a terminal with arguments (e.g. `add_packages.cmd requests numpy>=2`).
`Dev Menu.cmd` lists all of them. Every tool validates `developer_settings.py` first and
prepares the environment if needed; tools may download (unlike normal launches with
`allow_downloads_at_launch = False`). Close running app instances before changing packages
or Python — Windows locks the files they use.

| Tool | What it does |
| --- | --- |
| `add_packages.cmd [names]` | `uv add`: resolves and installs the packages, adds them to `packages` in `developer_settings.py` and updates `backend/uv.lock`. Asks for names when none are given. |
| `remove_packages.cmd [names]` | `uv remove`: lists `packages` and removes the chosen ones. |
| `upgrade_packages.cmd [names]` | `uv lock --upgrade` (or `--upgrade-package` for the named ones), then an exact sync. Test the app and commit `uv.lock`. |
| `sync_packages.cmd` | Makes `backend/.venv` match `uv.lock` exactly; removes packages installed by hand. |
| `find_imports.cmd` | Offline import finder: scans the code folder (not `backend/`), drops the standard library and your own modules, maps imports to packages (installed metadata first, then `DONT_CHANGE/data/import_to_package.txt`, else the import name — marked "guess"). Optional imports (inside `try/except ImportError`) start unchecked. Review, then the checked ones are added with `uv add` (and recorded in `packages`). |
| `package_terminal.cmd` | Command prompt in `code/` with the environment activated and uv on PATH: `uv add`, `uv pip list`, `python ...` (uv commands use the project in `backend/`; `uv add`/`uv remove` are copied into `packages` on the next start). `uv pip install NAME` installs without recording (the next exact sync removes it). |
| `change_python.cmd [version]` | Writes a new `python_version` into the settings and runs the migration menu (re-lock keeping versions / upgrade / empty package list / keep / write back). |
| `update_python.cmd` | Installs the newest patch release of the project's Python and rebuilds the environment if needed. With `python_version = ""` it also offers a newer minor version. System Pythons are updated with their own installers. |
| `make_portable.cmd` | Copies uv into `backend/uv`, installs the project's Python into `backend/pythons`, rebuilds the environment on it, then shows and optionally applies the settings that make launches use them (`uv_prefer`, `uv_install_if_missing`, `python_source`, `package_environment`). |
| `export_requirements.cmd` | Writes `backend/requirements.txt` (pinned, without hashes) from `uv.lock` for tools that need that format. |
| `status.cmd` | Settings validity, uv (version, local/global), launcher Python, `.python-version`, `requires-python`, `packages` (and whether `pyproject.toml` matches), environment base/relocatability, lock state, shortcuts. |
| `clean.cmd` | Deletes logs, crash logs or per-run diagnostics. |
| `remove_shortcuts.cmd` | Removes every shortcut Setup created (project folder, Start Menu, Desktop). Run Setup to create them again. |

## Typical workflows

- **New dependency:** add it to `packages` in `developer_settings.py` and start the app, or `add_packages.cmd requests` → test → commit `developer_settings.py` and `backend/uv.lock`.
- **Existing code with imports:** `find_imports.cmd` → review → add.
- **New Python version:** `change_python.cmd 3.13` → option 1 → test → commit `developer_settings.py`, `backend/.python-version` and `backend/uv.lock`.
- **Hand over an offline folder:** `make_portable.cmd` → accept the settings → optionally `allow_downloads_at_launch = False` → copy the folder → run Setup on the target PC for shortcuts.

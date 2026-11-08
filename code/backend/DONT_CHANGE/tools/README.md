# Launcher development tools

Tools for working on the launcher in `code/backend/DONT_CHANGE`, not for your app. The launcher never uses this folder, so deleting it doesn't affect anything.

Double-click a `.bat`, or run it from a terminal with arguments. Each one uses the Python the launcher has already set up.

| Tool | What it does |
| --- | --- |
| `verify_launcher.bat [--fix]` | Runs Ruff lint (including pathlib `PTH` and security `S` checks), Ruff format and strict Pyrefly on `DONT_CHANGE`, targeting Python 3.8 with its own `ruff.toml` and `pyrefly.toml`. Prints diagnostics and a warning for each check that reports problems; exits nonzero if any check fails. `--fix` applies safe fixes and formatting first; `--unsafe-fixes` also applies Ruff's unsafe ones. Needs `ruff` and `pyrefly` on PATH, or `uvx`. |
| `get_startup_time.bat` | Measures the time from starting a shortcut's launcher until the main script runs, compared with starting it directly with the `.venv` Python. Works on a temporary copy of the project. Options: `--runs`, `--timeout`, `--targets` (`terminal`, `no_terminal`, `direct`), `--keep`. |
| `get_import_times.bat launcher` | Shows what importing the launcher's own modules adds to an empty interpreter start. Option: `--runs`. |
| `get_import_times.bat app [modules]` | The same for the app's packages in `.venv`; without module names it measures everything in `packages`. |
| `make_import_map.bat` | Regenerates `data/import_to_package.txt`, the import name to PyPI project list that `find_imports` uses for packages that aren't installed yet. Needs internet and takes a few minutes; progress is cached in `DONT_CHANGE/tmp`, so an interrupted run continues. Options: `--count` (default 8000), `--workers`, `--output`, `--cache`. |
| `show_longest_paths.bat [count] [folder]` | Lists the longest paths in the project, including ignored ones such as `.venv` and `__pycache__` files that don't exist yet, and whether they exceed the Windows path limit. Press a key to measure again. |

The code these files run is in `../scripts/tools`.

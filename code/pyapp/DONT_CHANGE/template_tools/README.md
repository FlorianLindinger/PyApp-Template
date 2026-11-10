# Launcher development tools

Tools for working on the launcher in `code/pyapp/DONT_CHANGE`, not for your app. The launcher never uses this folder, so deleting it doesn't affect anything.

Double-click a `.bat`, or run it from a terminal with arguments. Each one uses the Python the launcher has already set up. When it finishes, press Enter to run it again, with the same arguments, or close the window.

| Tool | What it does |
| --- | --- |
| `verify_launcher.bat [--fix]` | Runs Ruff lint (including pathlib `PTH` and security `S` checks), Ruff format and strict Pyrefly on `DONT_CHANGE`, targeting Python 3.8 with its own `ruff.toml` and `pyrefly.toml`. Prints diagnostics and a warning for each check that reports problems; exits nonzero if any check fails. `--fix` applies safe fixes and formatting first; `--unsafe-fixes` also applies Ruff's unsafe ones. Needs `ruff` and `pyrefly` on PATH, or `uvx`. |
| `fresh_clone_test.bat [--timeout] [--keep]` | Clones the current commit into a temporary folder, runs Setup, starts the launcher without a terminal and runs a dev tool, which finds files missing from Git. Only committed files are tested, and it lists what isn't committed. `main.py` in the clone is replaced by a probe, and Setup there leaves your Start Menu and Desktop alone. |
| `test_all_pythons.bat [versions] [--pattern]` | Runs the regression tests on Python 3.8 and the newest stable Python, or on the versions you name. The Pythons are kept in your temporary folder. |
| `release.bat [patch\|minor\|major\|X.Y.Z]` | Checks that a release is possible, runs the tests, sets `LAUNCHER_VERSION`, turns the `## unreleased` changelog section into `## <version> - <date>` and writes a zip of the tracked `DONT_CHANGE` files to `dist/`. Without a version it only checks. It refuses uncommitted changes unless you pass `--allow-dirty`, and commits nothing. It does not offer to run again. |
| `src/git_hooks/pre-push` | Stops a push whose commits contain secrets or personal data, including private commit emails. Turn it on in a clone with `git config core.hooksPath code/pyapp/DONT_CHANGE/template_tools/src/git_hooks`. Git runs it during a push, not you; `git push --dry-run` tests it and `git push --no-verify` skips it once. |
| `check_git_leaks.bat [--no-history]` | Looks for secrets (token formats, private keys, passwords in code, secret files) and personal data (home folder paths, email addresses, machine files) in the files Git would publish and in every commit. Secrets are masked; exits nonzero if any are found. Put `leak-check: ignore` on a line to accept it. It finds common formats and cannot prove that a repository is clean. |
| `get_startup_time.bat` | Measures the time from starting a shortcut's launcher until the main script runs, compared with starting it directly with the `.venv` Python. Works on a temporary copy of the project. Options: `--runs`, `--timeout`, `--targets` (`terminal`, `no_terminal`, `direct`), `--keep`. |
| `get_import_times.bat launcher` | Shows what importing the launcher's own modules adds to an empty interpreter start. Option: `--runs`. |
| `get_import_times.bat app [modules]` | The same for the app's packages in `.venv`; without module names it measures everything in `packages`. |
| `make_import_map.bat` | Regenerates `data/import_to_package.txt`, the import name to PyPI project list that `find_imports` uses for packages that aren't installed yet. Needs internet and takes a few minutes; progress is cached in `DONT_CHANGE/tmp`, so an interrupted run continues. Cached projects older than 30 days are read again. Options: `--count` (default 8000), `--workers`, `--output`, `--cache`, `--max-age-days`, `--refresh` (read every project again). |
| `show_longest_paths.bat [count] [folder]` | Lists the longest paths in the project, including ignored ones such as `.venv` and `__pycache__` files that don't exist yet, and whether they exceed the Windows path limit. |

The code these files run is in `src`.

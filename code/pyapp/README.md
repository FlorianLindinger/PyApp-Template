# code/pyapp

Everything that makes your Python code a Windows app: its settings, the launcher, the
environment it runs in, its icons and tools. Your own code lives one folder up, in `code/`
(`main.py`, `settings.py` and your modules); here you mostly edit `developer_settings.py`.

## Overview

| Item | What it is | You | Git |
| --- | --- | --- | --- |
| [developer_settings.py](developer_settings.py) | All settings of the app: name, Python, packages, shortcuts, logs, windows | edit | commit |
| [Developer Tools.cmd](Developer%20Tools.cmd) | Menu of all developer tools | use | commit |
| [dev_tools/](dev_tools/README.md) | Double-click tools: packages, Python version, tests, status, cleanup | use | commit |
| [icons/](icons/README.md) | The app's icons, all made from `icon.png` | replace `icon.png` | commit |
| [tests/](tests/test_example.py) | The app's own tests (`test_*.py`) | add tests | commit |
| [generated/](generated/README.md) | What the launcher creates: the locked packages, the Python version, the environment | leave alone | partly |
| [Start without launcher.cmd](Start%20without%20launcher.cmd) | Starts the app when the launcher itself is broken | use if needed | commit |
| [Start without launcher --LINUX.sh](Start%20without%20launcher%20--LINUX.sh) | Direct Linux start with Python chosen in the shell file | use on Linux | commit |
| [DONT_CHANGE/](DONT_CHANGE/README.md) | The launcher; replaced as a whole to update it | don't edit | commit |
| `.gitignore` | Keeps the environment, caches and per-PC files out of Git | rarely | commit |

## Git protection

This folder's `.gitignore` starts with `!/**/*`, keeping source, settings, tools, icons and
tests eligible for Git even when a parent file ignores their extensions or subfolder names.
Later rules exclude Python bytecode, virtual environments and tool caches again. More deeply
nested ignore files still control launcher temporary files, test temporary files and release zips.

`generated/` is ignored by default. Its four portable files are explicitly included:
`README.md`, `uv.lock`, `.python-version` and `auto_generated_icons.json`. New local runtime
files and browser keys therefore remain ignored without needing another blacklist entry.

If an ancestor rule ignores `code/` or `code/pyapp/` itself, Git never reaches this file.
Re-include those directories in the root `.gitignore`, after the conflicting rule:

```gitignore
!/code/
!/code/pyapp/
```

These rules make untracked files eligible for `git add`; they do not automatically stage,
commit or push them. Ignore rules do not remove files that are already tracked.
Use `pyapp_tools/check_repository.bat --why PATH` inside `DONT_CHANGE` to explain a rule.

## Direct start on Linux

From `code/pyapp`, run:

```sh
sh "Start without launcher --LINUX.sh"
```

You can also pass its full path from another working folder. Arguments after the filename are
passed unchanged to the app. Choose Python at the top of the shell file (Python 3.8+):

```sh
python_command=""                         # first working python3/python on PATH
python_command="python3.12"               # an installed version on PATH
python_command="/usr/bin/python3"         # an explicit executable
python_command="/home/me/my env/bin/python" # an existing environment, if you want one
```

Use one executable without arguments; relative paths containing `/` start at the shell file's
folder. An invalid explicit selection reports an error rather than choosing another Python.
The script does not inspect or create `generated/.venv`, install Python or install packages.
The selected Python must already have the app's dependencies installed.
The script reads literal settings for the main file, arguments, environment and package list
without executing `developer_settings.py`, then runs the app from the main script's folder.
The `code` folder is included on the import path after the main script's folder, matching the launcher.
Windows backslashes in configured relative file paths are accepted. This direct start does
not install packages or provide the Windows launcher's shortcuts, logs or crash handling.
The app itself must support Linux. The Windows `.ico` is not injected into the Linux app environment.

## developer_settings.py

The one file to configure the app, read by the launcher at every start; each setting is explained
in a comment above it. Among them:

- `program_name`, `main_script_path` (default `../main.py`), and arguments and environment variables for it;
- `python_version`, and `packages` (one requirement per line, like a requirements.txt) or `requirements_path`;
- which shortcuts Setup makes and where (`start_menu_shortcuts`, `desktop_shortcuts`, the `*_shortcut_name` settings);
- logs and crash logs, and what happens when the program ends (close, stay open, a sound, open the log);
- the window: classic console or Windows Terminal (`use_classic_terminal`), colors, one instance or several (`instance_policy`);
- where uv and Python come from (`python_source`, `uv_*`), and the GitHub Actions an app can switch on (`github_actions`).

A mistake in the file is reported with its line at the next start. A setting missing in an older
file gets its default from `DONT_CHANGE/data/dev_settings_default.py`.

## dev_tools/

One `.cmd` per task; [`Developer Tools.cmd`](Developer%20Tools.cmd) here in `code/pyapp` lists them all. Each checks the settings and brings the
environment up to date first. Details: [dev_tools/README.md](dev_tools/README.md).

- Packages: `list_packages` (what is installed and why), `outdated_packages`, `add_packages`,
  `remove_packages`, `upgrade_packages`, `sync_packages`, `find_imports`, `export_requirements`,
  `package_terminal`.
- Python: `change_python`, `update_python`.
- Project: `run_tests`, `status`, `clean`, `remove_shortcuts`, `make_self_contained` (makes the
  folder run on other PCs without internet).

## icons/

`icon.png` is the picture; `regenerate icons.cmd` makes the window and shortcut icons from it,
each with a small symbol (Settings, STOP, Logs, ...), at every size Windows needs. Replace
`icon.png`, regenerate, then run Setup so the shortcuts show the new icons. A single `.ico` can
also be replaced by your own: the generator asks before replacing it. Details, including which
icon is shown where: [icons/README.md](icons/README.md).

## tests/

The app's own tests: files named `test_*.py` with `unittest.TestCase` classes (or pytest
functions, once pytest is in `packages`). `dev_tools/run_tests.cmd` runs them with the app's
environment; a `tests` folder in `code/` is found too. `test_example.py` checks that every Python
file of the app compiles and shows how a test looks.

## generated/

Created and kept up to date by the launcher; you normally change nothing here. Commit `uv.lock`
(the exact package versions), `.python-version` and `auto_generated_icons.json`. The rest is per
PC and ignored by Git: `pyproject.toml` (made from `packages`; a `uv add` made in it is copied
back into `packages`), the environment `.venv/`, and, depending on the settings, a local uv,
Python and download cache. Deleting `.venv/` is safe: the next start rebuilds it. Details:
[generated/README.md](generated/README.md).

## Start without launcher.cmd

If the launcher itself is broken, this still starts the app: with the app's environment
(`generated/.venv`), or with the global default Python when that is missing or broken. It first
shows the main script, Python, the packages (installed or missing) and their folders. There is
no setup, no package installation, no log, no crash log and no STOP shortcut; run Setup to repair
the launcher. Its code is `DONT_CHANGE/actions/start_without_launcher.py`, which uses nothing
else of the launcher.

## DONT_CHANGE/

The launcher: the batch files the shortcuts start, the Python code that prepares the environment
and runs the app, its data and its own tests. To update it, replace the whole folder with the
one of a newer template version; everything else in your project stays. What it keeps the same
between versions (file names, commands, settings) is listed in `backend_settings.py`
(`PROTECTED_*`). How it works: [DONT_CHANGE/README.md](DONT_CHANGE/README.md); changes:
[DONT_CHANGE/CHANGELOG.md](DONT_CHANGE/CHANGELOG.md).

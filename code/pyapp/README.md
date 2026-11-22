# code/pyapp

Everything that makes your Python code a Windows app: its settings, the launcher, the
environment it runs in, its icons and tools. Your own code lives one folder up, in `code/`
(`main.py`, `settings.py` and your modules); here you mostly edit `developer_settings.py`.

## Overview

| Item | What it is | You | Git |
| --- | --- | --- | --- |
| [developer_settings.py](developer_settings.py) | All settings of the app: name, Python, packages, shortcuts, logs, windows | edit | commit |
| [Open Developer Tools Menu.cmd](Open%20Developer%20Tools%20Menu.cmd) | Menu of all developer tools | use | commit |
| [compilation/](compilation/README.md) | Settings for building an .exe (or a Linux version) of the app; `Compilation Tools.cmd` | edit if you build | commit |
| `compiled/` | The builds, made by the compilation tools | leave alone | ignored |
| [icons/](icons/README.md) | The app's icons, all made from `icon.png` | replace `icon.png` | commit |
| [generated/](generated/README.md) | What the launcher creates: the locked packages, the Python version, the environment | leave alone | partly |
| [fallback_start/](fallback_start/Start%20without%20launcher.cmd) | `Start without launcher.cmd` starts the app when the launcher itself is broken; `Start without launcher --LINUX.sh` starts it on Linux | use if needed | commit |
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

From `code/pyapp/fallback_start`, run:

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
without executing `developer_settings.py`, then runs the app from `working_directory` when
configured (absolute or relative to developer settings), otherwise the main script's folder.
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

`show_splash_screen_for_no_terminal_start = True` shows a branded, animated startup card with the app's name and
`icons/icon.png` while its environment is prepared, only for no-terminal starts. Set it to `False` to disable it.
`splash_screen_messages` lists lines for under the name; each start shows the next one.
It closes when the launcher starts `main.py`; no-terminal starts keep it visible for at
least 0.5 seconds in parallel, without delaying the app. It does not wait for the app's GUI to load.
Minimized starts skip it, and it needs no extra packages. See
[startup splash details](DONT_CHANGE/docs/RUNTIME_SETTINGS.md#startup-splash) for bootstrap
and Tkinter availability limits.

## Developer tools

Double-click [`Open Developer Tools Menu.cmd`](Open%20Developer%20Tools%20Menu.cmd) for a numbered
menu of every tool, or give it a command in a terminal opened in `code/pyapp`:

```bat
"Open Developer Tools Menu.cmd" add requests "numpy>=2"
"Open Developer Tools Menu.cmd" sync
"Open Developer Tools Menu.cmd" change-python 3.13
```

Quote requirements with `<`, `>` or `|`, which the command prompt would otherwise treat as
redirection. Every tool checks `developer_settings.py` first and brings the environment up to
date if needed. Close running app instances before changing packages or Python: Windows locks
the files they use.

| Command | What it does |
| --- | --- |
| `list-packages [--outdated]` | What is installed and why: the main packages with their limit, locked version and how many dependencies each brings in, then every dependency with the packages that need it. Shows packages that are missing, at another version or installed by hand (`sync` fixes them), and main packages no file in `code/` imports. `--outdated` also asks PyPI for newer versions. Changes nothing. |
| `add [names]` | `uv add`: installs the packages, adds them to `packages` in `developer_settings.py` and updates `generated/uv.lock`. Asks for names when none are given. |
| `remove [names]` | Lists `packages` and removes the chosen ones. |
| `clear-packages` | Lists `packages`, asks, then empties it and syncs (back to 0 packages). The `requirements_path` file is kept. |
| `upgrade [names]` | Upgrades all (or the named) packages within their limits, then syncs. Test the app and commit `uv.lock`. |
| `sync` | Makes `generated/.venv` match `uv.lock` exactly and lists what it added or removed. |
| `find-imports` | Scans the code folder offline for imports, maps them to packages and adds the ones you keep checked. Optional imports start unchecked. |
| `reset-imports` | Replaces `packages` with what the code imports, after review. Keeps existing version limits. Static analysis misses plugins and dynamic imports: review removals. |
| `install-requirements [path]` | `uv add -r`: adds the packages of a requirements file to `packages`. For a file that should stay the source of truth, use `requirements_path` instead. |
| `terminal` | A command prompt with the environment active and uv on PATH. `uv add`/`uv remove` there are copied into `packages` on the next start; `uv pip install` is not recorded. |
| `export` | Writes `pyapp/requirements.txt` (pinned) from `uv.lock` for tools that need that format. |
| `change-python [version]` | Sets a new `python_version` and migrates: keep package versions, upgrade them, start with no packages, or undo. |
| `update-python` | Installs the newest patch release of the project's Python (with a loose `python_version` also a newer minor version) and rebuilds the environment if needed. |
| `compilation` | Opens the compilation menu; see [compilation/](compilation/README.md). |
| `test-linux` | Starts the app on Linux inside WSL (Windows' built-in Linux) so you can see it run. Offers to install WSL with Ubuntu (administrator rights, maybe a restart) and Python with tkinter in Linux first. The app's packages are not installed there. |
| `run-tests [arguments]` | Runs the app's tests in `code/tests`; arguments go to pytest or unittest. |
| `status` | Settings, uv, Python, environment, lock file, shortcuts and errors the launcher ignored on purpose. Works without uv. |
| `clean` | Deletes logs, crash logs or per-run diagnostics. |
| `remove-shortcuts` | Removes every shortcut Setup created. Run Setup to create them again. |
| `make-self-contained` | Copies uv and Python into `generated/` and switches the settings to them, so the folder runs on other PCs without internet. Shows what it changes and asks first. |
| `test` | The launcher's own tests (`DONT_CHANGE/tests`), for template development. |

Typical workflows:

- **New dependency:** add it to `packages` and start the app, or run `add requests` → test →
  commit `developer_settings.py` and `generated/uv.lock`.
- **Existing code with imports:** `find-imports` → review → add.
- **New Python version:** `change-python 3.13` → keep versions → test → commit
  `developer_settings.py`, `generated/.python-version` and `generated/uv.lock`.
- **A folder that runs offline on another PC:** `make-self-contained` → copy the whole folder
  (a Git clone lacks the local uv, Python and packages) → run Setup there once.

## icons/

`icon.png` is the picture; `regenerate icons.cmd` makes the window and shortcut icons from it,
each with a small symbol (Settings, STOP, Logs, ...), at every size Windows needs. Replace
`icon.png`, regenerate, then run Setup so the shortcuts show the new icons. A single `.ico` can
also be replaced by your own: the generator asks before replacing it. Details, including which
icon is shown where: [icons/README.md](icons/README.md).

## The app's tests: code/tests

The app's own tests live next to its code, in `code/tests`: files named `test_*.py` with
`unittest.TestCase` classes (or pytest functions, once pytest is in `packages`).
`code/tests/run_all_tests.cmd` (or `run-tests` in the developer tools) runs them with the app's
environment. `test_example.py` checks that every Python file of the app compiles and shows how a
test looks. What only the tests import (pytest, ...) is not suggested by *find-imports*.

## generated/

Created and kept up to date by the launcher; you normally change nothing here. Commit `uv.lock`
(the exact package versions), `.python-version` and `auto_generated_icons.json`. The rest is per
PC and ignored by Git: `pyproject.toml` (made from `packages`; a `uv add` made in it is copied
back into `packages`), the environment `.venv/`, and, depending on the settings, a local uv,
Python and download cache. Deleting `.venv/` is safe: the next start rebuilds it. Details:
[generated/README.md](generated/README.md).

## fallback_start/

If the launcher itself is broken, `Start without launcher.cmd` still starts the app: with the app's environment
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

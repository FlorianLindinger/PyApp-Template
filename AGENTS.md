# AGENTS.md

Guidance for AI coding agents working in a project made from PyApp-Template. The template turns a
Python script or GUI into a Windows app: Setup creates shortcuts, and a launcher installs uv, the
pinned Python and the locked packages, runs the app and writes logs and crash reports.
[README.md](README.md) explains it for people.

## Where to edit

| Path | What it is |
| --- | --- |
| `code/main.py` and other modules in `code/` | The app. `main_script_path` in `developer_settings.py` names the main file. |
| `code/settings.py` | Optional settings for the people using the app, read with `import settings`. |
| `code/pyapp/developer_settings.py` | The app's name, Python version, packages and behavior. Each setting is documented in the file. |
| `code/tests/` | The app's tests (`test_*.py`, pytest or unittest). |
| `code/pyapp/icons/icon.png` | The source image for every icon. |

Do not edit these:

- `code/pyapp/DONT_CHANGE/` is the launcher. Updates replace the whole folder, so any change is
  lost. If the launcher seems to be the problem, report it instead of patching it.
- `code/pyapp/generated/` is written by the launcher. `pyproject.toml` is regenerated from
  `developer_settings.py`, and `uv.lock` changes only through the package tools below.

## Commands

Run these from the repository root in `cmd` or PowerShell. Set `PYAPP_ENTRYPOINT_NO_PAUSE=1` first,
otherwise each command waits for Enter at the end. A tool that asks a question treats closed
input as "cancel", so pass the arguments it needs.

| Task | Command |
| --- | --- |
| Add packages | `code\pyapp\DONT_CHANGE\B\run.bat dev add requests "numpy>=2"` |
| Remove packages | `code\pyapp\DONT_CHANGE\B\run.bat dev remove requests` |
| Show packages and anything that differs from `uv.lock` | `code\pyapp\DONT_CHANGE\B\run.bat dev list-packages` |
| Make the environment match `uv.lock` | `code\pyapp\DONT_CHANGE\B\run.bat dev sync` |
| Run the app's tests (arguments go to pytest/unittest) | `code\pyapp\DONT_CHANGE\B\run.bat dev run-tests -v` |
| Run the app's tests and keep the window open | `code\tests\run_all_tests.cmd` (waits for a key at the end) |
| Show uv, Python, environment and shortcut state | `code\pyapp\DONT_CHANGE\B\run.bat dev status` |
| Regenerate the icons from `icon.png` | `code\pyapp\DONT_CHANGE\B\run.bat icons` |
| Recreate the shortcuts (after moving the folder or changing shortcut settings or icons) | `code\pyapp\DONT_CHANGE\B\run.bat setup` |

`code\pyapp\Open Developer Tools Menu.cmd` lists every tool and runs one when given its name;
[code/pyapp/README.md](code/pyapp/README.md#developer-tools) describes them. The app's Python is `code\pyapp\generated\.venv\Scripts\python.exe`.

## Rules

- **Packages:** they go in the `packages` block of `developer_settings.py`, either through
  `dev add` / `dev remove` or by editing the block. Never `pip install` or `uv pip install`
  into the environment: such a package is not recorded, and the next exact sync removes it.
- **Python version:** change `python_version` only when asked. Switching needs a migration that
  `dev change-python` runs, and it asks questions.
- **Launcher helpers:** prefer `import pyapp_api` (notifications, `on_stop` for saving on Stop or
  close, taskbar progress, dialogs, `keep_awake`, `report_error`, `restart`) over writing your own;
  every function is safe without the launcher. See the README section on `pyapp_api`.
- **Values from the launcher:** read them with a fallback, e.g.
  `os.environ.get("PROGRAM_NAME", "My App")` or `os.environ.get("ICON_PATH")`, so the app also
  runs with plain `python main.py`. The README section "Talking to the launcher" lists every variable.
- **Imports and paths:** the `code` folder is always on the import path. Don't assume a
  particular working folder; build paths from `__file__` instead.
- **Platform:** the launcher is Windows only. Keep `.cmd` and `.bat` files with CRLF line endings.
- **Git:** commit `code/pyapp/generated/uv.lock`, `.python-version` and
  `auto_generated_icons.json` together with the change that produced them. Never commit
  `generated/.venv`, `generated/browser_terminal_key.txt`, `logs/` or `crash logs/`.

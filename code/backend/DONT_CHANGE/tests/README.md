# Launcher tests

Regression tests for the launcher in `code/backend/DONT_CHANGE` (not for your app). They need
any Python 3.8+ and only the standard library; nothing is downloaded, and everything they change
is a temporary copy, so they are safe to run at any time.

Run them after changing anything in `DONT_CHANGE`, or after updating the template:

- double-click `run_launcher_tests.cmd` in this folder (uses the launcher's Python), or
- from a terminal in this folder: `python run_regressions.py` (all, about 10 s) or
  `python run_regressions.py test_wrapper.py` (one file); `-q` prints one dot per test.

`test_windows.py` runs on Windows only. Deleting this folder does not affect the launcher.

| File | Covers |
| --- | --- |
| `test_settings.py` | validation of every setting, friendly errors for mistakes in `developer_settings.py`, `[bootstrap]` rules, the defaults file matching the template's `developer_settings.py`, editing settings (quotes, comments, CRLF, last definition) |
| `test_packages.py` | generated `pyproject.toml` round trip (markers, quotes, comments), copying `uv add` back, settings win on conflict, `requires-python`, the launch fast-path fingerprint |
| `test_wrapper.py` | `script_wrapper.py` in a real interpreter: arguments, hidden launcher variables, no shadowing of the app's `protocol.py`, reports for exceptions, `SystemExit`, missing modules, `os._exit`, late worker-thread errors, log and print prefixes |
| `test_tracebacks.py` | exception chains, suppressed context, notes and groups (3.11+), success rules, the explicit exit-code mapping, rendering |
| `test_uv_fallback.py` | installing a Python retries once with a newer uv, and reports the error when none is available |
| `test_icons.py` | icons always use the bundled overlays; generated icons update silently, a question per icon for placed ones |
| `test_imports.py` | stdlib/local/launcher exclusions, nested `backend` folders, optional-import guards, unparsable files, installed metadata, the mapping file |
| `test_banner.py` | the expected banner font is shipped, renders the app name, supports German letters and Latin-1, and skips missing characters |
| `test_entrypoint.py` | exit codes, prompts (`pause_on_success`), class-based expected problems, the `entrypoint.py <tool>` runner |
| `test_logs.py` | log paths, unique names, diagnostics log, taskbar identity per folder, shortcut file names, outdated shortcut targets |
| `test_files.py` | CRLF batch files, every referenced script exists, every tool has `main()`, lint configs, Python 3.8 compatibility of the launcher |
| `test_windows.py` | Windows only: registry records with job names, Stop ends the whole job (incl. grandchildren), graceful Stop via Ctrl+C, file lock |

Manual release check (not automated): Setup, start twice, Stop on the example window, the
open shortcuts, `status.cmd`, `change_python`, `make_portable`, a moved and a copied folder.

# Launcher tests

Regression tests for the launcher in `code/pyapp/DONT_CHANGE` (not for your app). They need
any Python 3.8+ and only the standard library; nothing is downloaded, and everything they change
is a temporary copy, so they are safe to run at any time.

Run them after changing anything in `DONT_CHANGE`, or after updating the template:

- double-click `run_launcher_tests.cmd` in this folder (uses the launcher's Python), or
- from a terminal in the `src` folder: `python run_regressions.py` (all, about 10 s one after another).

The launchers are in this folder, the test code in `src`. The tests are sorted into groups
(below), each with its own launcher:
`run_app_tests.cmd`, `run_setup_tests.cmd`, `run_browser_tests.cmd`, `run_git_tests.cmd`,
`run_tools_tests.cmd` and `run_files_tests.cmd`. From a terminal, name one or more groups or file
patterns: `python run_regressions.py browser`, `python run_regressions.py setup git` or
`python run_regressions.py test_wrapper.py`. `--list` shows the groups, `-q` prints one dot per
test, and `-j 0` runs the test files in parallel, one process each (about 5 s; the pre-push hook
uses it). `src/groups.py` defines the groups; a new test file must be added to one of them
(`test_files.py` checks this).

`test_windows.py` runs on Windows only. Deleting this folder does not affect the launcher.

### `app`: starting and ending an app

| File | Covers |
| --- | --- |
| `test_entrypoint.py` | exit codes, prompts (`pause_on_success`), class-based expected problems, the `entrypoint.py <tool>` runner, app modules named like stdlib modules |
| `test_wrapper.py` | `script_wrapper.py` in a real interpreter: arguments, hidden launcher variables, no shadowing of the app's `protocol.py`, reports for exceptions, `SystemExit`, missing modules, `os._exit`, late worker-thread errors, log and print prefixes |
| `test_tracebacks.py` | exception chains, suppressed context, notes and groups (3.11+), success rules, the explicit exit-code mapping, rendering |
| `test_output_logs.py` | crash logs contain the app's prints; the raw output file is only kept after failures; the hidden completion handler never waits |
| `test_logs.py` | log paths, unique names, diagnostics log, `clean` (only the launcher's own logs, files in use, run folders), crash exit codes, unreadable process records |
| `test_shortcuts.py` | shortcut file names and order, outdated shortcut targets, taskbar identity per folder, removing shortcuts |
| `test_console_colors.py` | only hexadecimal color arguments can reach the Windows color command; a failure turns the window black; the `wt.exe` command line |
| `test_banner.py` | the banner font renders the app name, supports German letters and Latin-1, skips missing characters; the console font it needs |
| `test_icons.py` | icons always use the bundled overlays; generated icons update silently, a question per icon for placed ones; small sizes in linear light; every `.ico` size |
| `test_dev_menu.py` | the dev tools menu offers every command exactly once; every prompt can be cancelled; missing-package recovery |
| `test_fallback.py` | `actions/start_without_launcher.py` from a copy that has nothing else of the launcher: settings, arguments, environment, exit code, missing packages, unreadable settings |
| `test_windows.py` | Windows only: registry records with job names, Stop ends the whole job (incl. grandchildren), graceful Stop via Ctrl+C, file lock |

### `setup`: settings, environment, uv and Python

| File | Covers |
| --- | --- |
| `test_settings.py` | validation of every setting, friendly errors for mistakes in `developer_settings.py`, `[bootstrap]` rules, the defaults file matching the template's `developer_settings.py`, editing settings (quotes, comments, CRLF, last definition) |
| `test_packages.py` | generated `pyproject.toml` round trip (markers, quotes, comments), copying `uv add` back, settings win on conflict, `requires-python`, `requirements_path`, nothing changes while the app runs, the launch fast-path fingerprint |
| `test_resolve_runtime.py` | `bootstrap/resolve_runtime.py`: settings, `uv_version` rules, messages for company PCs, the uv download folder, the runtime cache |
| `test_uv_fallback.py` | installing a Python retries once with a newer uv, and reports the error when none is available |
| `test_imports.py` | stdlib/local/launcher exclusions, nested `pyapp` folders, optional-import guards, unparsable files, installed metadata, the mapping file |
| `test_app_workflows.py` | `github_actions`: Setup creates, updates and removes only its own workflow files |
| `test_template_workflows.py` | Setup deletes the template's own workflows only in an app, only unchanged and alone; every template workflow job is skipped outside PyApp-Template |

### `browser`: the browser terminal

| File | Covers |
| --- | --- |
| `test_browser_terminal.py` | the launcher side: its shortcut, stable address and start link (never another program's), the console check that ignores an inherited variable |
| `test_host.py` | in `browser_terminal/tests`, the package itself: a real pseudoconsole, input, Ctrl+C, UTF-8, start at the page's size, icon/color/notify requests, file links, only the page may connect, a copy of the folder runs on its own |

### `git`: the Git hooks and their checks

| File | Covers |
| --- | --- |
| `test_git.py` | no ignore rule hides a launcher file |
| `test_git_hooks.py` | Real shell hooks in disposable repositories: failure diagnostics reach stderr and push refs reach the check |
| `test_git_leaks.py` | `pyapp_tools/check_git_leaks`: what counts as a leak; secrets are never printed in full |
| `test_staged_ruff.py` | `pyapp_tools/check_staged_ruff` (pre-commit hook): Ruff on the staged launcher files |
| `test_check_all.py` | `pyapp_tools/check_all` (pre-push hook): every check at once, with a summary |
| `test_repository_check.py` | `pyapp_tools/check_repository`: problems that break clones, other PCs or Windows |

### `tools`: the maintainer tools in `pyapp_tools`

| File | Covers |
| --- | --- |
| `test_release.py` | `pyapp_tools/release`: version numbers, the changelog and the zip |
| `test_tools.py` | `pyapp_tools/fresh_clone_test` and `test_all_pythons`: the parts that can be checked without a clone |
| `test_verify_launcher.py` | diagnostic warnings, tool errors, successful checks and continuing after a failed check |
| `test_import_map.py` | `make_import_map`: approved HTTPS download sources, redirect restrictions, range headers and byte responses without network access, the cache |

### `files`: static checks of the shipped files

| File | Covers |
| --- | --- |
| `test_files.py` | CRLF batch and settings files, every referenced script exists, every tool has `main()`, the README file tables, every test file in a group with its launcher |
| `test_python38.py` | Python 3.8 compatibility of the launcher: lint targets, syntax and library calls, annotations that runtime type inspection can evaluate |
| `test_template_contract.py` | what must stay stable: the repository name in the Actions, what existing projects expect in `DONT_CHANGE` (`run.bat` and the fallback start, which may only use the standard library) |

Manual release check (not automated): Setup, start twice, Stop on the example window, the
open shortcuts, `status.cmd`, `change_python`, `make_self_contained`, a moved and a copied folder.

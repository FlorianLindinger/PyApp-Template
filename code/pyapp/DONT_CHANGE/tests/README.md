# Launcher tests

Regression tests for the launcher in `code/pyapp/DONT_CHANGE` (not for your app). They need
any Python 3.8+ and only the standard library; nothing is downloaded, and everything they change
is a temporary copy, so they are safe to run at any time.

Run them after changing anything in `DONT_CHANGE`, or after updating the template:

- double-click `run_launcher_tests.cmd` in this folder (uses the launcher's Python), or
- from a terminal in this folder: `python run_regressions.py` (all, about 10 s one after another) or
  `python run_regressions.py test_wrapper.py` (one file); `-q` prints one dot per test, and
  `-j 0` runs the test files in parallel, one process each (about 5 s; the pre-push hook uses it).

`test_windows.py` runs on Windows only. Deleting this folder does not affect the launcher.

| File | Covers |
| --- | --- |
| `test_annotations.py` | runtime type inspection of settings, launcher functions, protocols and wrapper classes; annotation syntax evaluable on Python 3.8 |
| `test_settings.py` | validation of every setting, friendly errors for mistakes in `developer_settings.py`, `[bootstrap]` rules, the defaults file matching the template's `developer_settings.py`, editing settings (quotes, comments, CRLF, last definition) |
| `test_packages.py` | generated `pyproject.toml` round trip (markers, quotes, comments), copying `uv add` back, settings win on conflict, `requires-python`, the launch fast-path fingerprint |
| `test_wrapper.py` | `script_wrapper.py` in a real interpreter: arguments, hidden launcher variables, no shadowing of the app's `protocol.py`, reports for exceptions, `SystemExit`, missing modules, `os._exit`, late worker-thread errors, log and print prefixes |
| `test_tracebacks.py` | exception chains, suppressed context, notes and groups (3.11+), success rules, the explicit exit-code mapping, rendering |
| `test_uv_fallback.py` | installing a Python retries once with a newer uv, and reports the error when none is available |
| `test_icons.py` | icons always use the bundled overlays; the optional 32x32/16x16 images, never the template's with your own `icon.png`; generated icons update silently, a question per icon for placed ones |
| `test_imports.py` | stdlib/local/launcher exclusions, nested `pyapp` folders, optional-import guards, unparsable files, installed metadata, the mapping file |
| `test_import_map.py` | approved HTTPS download sources, redirect restrictions, range headers and byte responses without network access |
| `test_console_colors.py` | only hexadecimal color arguments can reach the Windows color command |
| `test_verify_launcher.py` | diagnostic warnings, tool errors, successful checks and continuing after a failed check |
| `test_banner.py` | the expected banner font is shipped, renders the app name, supports German letters and Latin-1, and skips missing characters |
| `test_entrypoint.py` | exit codes, prompts (`pause_on_success`), class-based expected problems, the `entrypoint.py <tool>` runner |
| `test_logs.py` | log paths, unique names, diagnostics log, taskbar identity per folder, shortcut file names, outdated shortcut targets |
| `test_files.py` | CRLF batch files, every referenced script exists, every tool has `main()`, lint configs, Python 3.8 compatibility of the launcher |
| `test_output_logs.py` | crash logs contain the app's prints; the raw output file is only kept after failures; the hidden completion handler never waits |
| `test_resolve_runtime.py` | `bootstrap/resolve_runtime.py`: settings, `uv_version` rules, messages for company PCs, the uv download folder |
| `test_dev_menu.py` | the dev tools menu offers every command exactly once; missing-package recovery |
| `test_template_workflows.py` | Setup deletes the template's own workflows only in an app, only unchanged and alone; every template workflow job is skipped outside PyApp-Template |
| `test_app_workflows.py` | `github_actions`: Setup creates, updates and removes only its own workflow files |
| `test_template_contract.py` | what must stay stable: the repository name in the Actions, what existing projects expect in `DONT_CHANGE` |
| `test_git.py` | no ignore rule hides a launcher file |
| `test_git_leaks.py` | `pyapp_tools/check_git_leaks`: what counts as a leak; secrets are never printed in full |
| `test_staged_ruff.py` | `pyapp_tools/check_staged_ruff` (pre-commit hook): Ruff on the staged launcher files |
| `test_check_all.py` | `pyapp_tools/check_all` (pre-push hook): every check at once, with a summary |
| `test_git_hooks.py` | Real shell hooks in disposable repositories: failure diagnostics reach stderr and push refs reach the check |
| `test_repository_check.py` | `pyapp_tools/check_repository`: problems that break clones, other PCs or Windows |
| `test_release.py` | `pyapp_tools/release`: version numbers, the changelog and the zip |
| `test_tools.py` | `pyapp_tools/fresh_clone_test` and `test_all_pythons`: the parts that can be checked without a clone |
| `test_browser_terminal.py` | the browser terminal: its shortcut, stable address and start link (never another program's), a copy of the `browser_terminal` folder runs on its own, tab or app window, colors, and the host with a real pseudoconsole: input, Ctrl+C, UTF-8, icon/color requests, exit code, only the page may connect, a closed page ends the program |
| `test_windows.py` | Windows only: registry records with job names, Stop ends the whole job (incl. grandchildren), graceful Stop via Ctrl+C, file lock |

Manual release check (not automated): Setup, start twice, Stop on the example window, the
open shortcuts, `status.cmd`, `change_python`, `make_self_contained`, a moved and a copied folder.

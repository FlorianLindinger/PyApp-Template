# Agent changelog

What coding agents changed in this `DONT_CHANGE` folder (and the files next to it that belong to
the launcher), newest last, with the checks that were run. One dated entry per task: files,
significant changes, checks and their results, and anything left open. `CHANGELOG.md` remains the
changelog for people updating the launcher.

## 2026-11-11 — REPOSITORY_AUDIT.md F01–F12

- F01 `scripts/entrypoint.py`, `runtime/bg_watchdog.py`, `runtime/process_exit.py`: code folder appended to `sys.path` instead of inserted first.
- F02 `scripts/env/venv.py`: fingerprint uses site-packages entry names (minus `__pycache__`) instead of the folder mtime; stamp version v2.
- F03 Removed `scripts/template_repo.py`, its test, and the Setup call; hooks are opt-in (`pyapp_tools/README.md`, CHANGELOG). Global `includeIf` setup was blocked by the permission classifier; left to the user.
- F04 `bg_watchdog.handle_exit`: hidden handler gets stdin=NUL and is re-run in a visible console on failure; `_fail_while_loading` tolerates EOF.
- F05 `process_exit.complete`: report printed before the crash log; `OSError` while writing it becomes one error line.
- F06 `scripts/config.py`: triple-quoted `packages` block is edited line by line (comments/blank lines kept, comment kept on version change); regenerated when the value has backslashes.
- F07 `config.terminal_color_code` fills the unset half (0/7); `validate` rejects equal colors.
- F08 `scripts/file_tools.remove_tree_inside`: links checked by their own location, removed without following.
- F09 `scripts/diagnostics.diagnostics_summary`: counts header lines.
- F10 `bootstrap/resolve_runtime.py` + `config.validate`: strict `uv_version` clause pattern.
- F11 `bootstrap/resolve_runtime.bat`: make_portable → make_self_contained.
- F12 batch stage deletes the uv archive/checksum after unpacking; `fetch_uv_folder` copies only `*.exe`.
- Tests added in test_entrypoint, test_packages, test_output_logs, test_settings, test_logs, test_resolve_runtime; each verified to fail on the old code.
- Checks: verify_launcher (Ruff 0.17.4 lint+format with DONT_CHANGE/ruff.toml, Pyrefly with DONT_CHANGE/pyrefly.toml): passed. run_regressions.py -j 0 on Python 3.14.9: 286 tests OK. Python 3.8 not installed, so not run.

## 2026-11-11 - REPOSITORY_AUDIT.md F13-F46 (without F34, F35, F44), hooks tool, tool minimums

- Fixed: F15 (`runtime_state`), F17 (`com_tools`), F19 (`env/pyproject`, package terminal help), F20 (`dev_tools/packages`), F21-F23 (`dev_tools/housekeeping`, `shortcuts`, `actions/setup`), F24, F25, F45 (`actions/start_program`, `runtime/bg_watchdog`, `backend_settings`), F26 (`shortcuts`, README, `get_startup_time`), F27 (READMEs, TODO, `tests/support.py`, new `test_the_file_tables_name_existing_files`), F28 (`image_tools`, annotation test walks all launcher modules), F29 (`tests/project_location`), F30-F32 (`bootstrap/resolve_runtime`, `env/pythons`, watchdog settings load), F33 (`check_git_leaks`: UTF-16, streamed history), F36, F37 (`isdecimal`), F38 (System32 paths in `backend_settings`), F40 (`console_tools`), F41 (`runtime_state`), F42 (`import_finder`: `pyvenv.cfg`, `site-packages`; not build/dist), F46 (`pyapp_tools/src/_run_tool.bat`, `setting()`, unused label, `.gitignore`).
- Not done, need a decision: F13, F14, F16, F18, F39, F43; shipping the template's own GitHub workflows.
- New `pyapp_tools/enable_git_hooks.bat` / `src/enable_git_hooks.py` (`--off`): local `core.hooksPath` plus a global `includeIf hasconfig:remote.*.url:<origin>**` to `~/.gitconfig-pyapp-hooks`. Tried against a temporary global config: matching clone gets the hooks, a clone of another owner does not, `--off` removes both. The real global config was not changed.
- Moved the agent changelog from the untracked root `AGENT_CHANGELOG.local.md` here (user request); removed its `.git/info/exclude` line.
- Tool minimums by bisecting PyPI releases with uvx: Ruff 0.17.0 (0.16.x reports a finding, older more), Pyrefly 1.4.0 (1.3.x and older: fatal configuration error on pyrefly.toml error names). `ruff.toml` `required-version = ">=0.17.0"`; `verify_launcher.tool_command` uses a PATH tool only if new enough, else `uvx --from "<tool>>=<min>"`.
- Tests: 305 OK on Python 3.14.9 (`run_regressions.py -j 0`); every new test fails on the old code. verify_launcher (Ruff 0.17.4 with ruff.toml, Pyrefly with pyrefly.toml): passed. Python 3.8 not installed, not run. No tests for F24 (race), F38, F40, F45.

## 2026-11-11 - Setup removes the template's own workflows from apps

- New `scripts/template_workflows.py`, called by `actions/setup.py` before `sync_app_workflows`; new `tests/test_template_workflows.py`; README rows (root, DONT_CHANGE, tests).
- Deletes `.github/workflows/pyapp-template-*.yml` and the then-empty folders only if: origin in `.git/config` is not `*/PyApp-Template` (no `.git` counts as an app; a `.git` file or unreadable config keeps everything), `.github` holds only `workflows`, `workflows` holds only those files, and each file's SHA-256 (CRLF->LF) is a published version.
- Hashes from every version in Git history; only versions whose every job has `if: endsWith(github.repository, '/PyApp-Template')` (checked for all nine). The older unguarded `fresh-clone.yml` / `launcher-tests.yml` are excluded, so a folder holding them is left alone. A test requires the current files to be listed and guarded.
- Checks: verify_launcher passed; 312 tests OK on Python 3.14.9; this repository is recognized as the template (nothing would be removed).

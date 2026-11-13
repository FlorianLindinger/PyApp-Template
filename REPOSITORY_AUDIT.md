# Repository Audit — PyApp-Template

Audit date: 2026-11-11 · Revision: `83d5d141bd8e61d3452679daaf218a198be69756` (branch `dev`) · Analysis only; no repository file other than this report was created or changed.

Path convention: `DC/` stands for `code/pyapp/DONT_CHANGE/`. Line numbers refer to the revision above.

---

## A. Executive summary

**Overall assessment.** The repository is in good shape for its size and age. The launcher is consistently structured, documented file by file, type-checked with a strict Pyrefly preset, linted with a broad Ruff rule set, and covered by 261 fast regression tests that pass on both ends of the supported Python range (3.8.20 and 3.14.9). Ruff lint, Ruff format and Pyrefly all report zero problems with the project's own configuration. Destructive operations are guarded (path containment checks, atomic writes, backups with rollback), subprocesses are started without a shell, and downloads are restricted to HTTPS with a checksum.

No Critical or High finding was identified. The findings that matter are six Medium ones, all of which sit at the seams between components rather than inside a single function, which is also why the existing unit tests do not catch them.

**Most important findings**

1. **F01** — The launcher puts the app's `code` folder *first* on its own `sys.path`. An app module named like a standard-library module the launcher imports lazily (`random.py`, `signal.py`, `json.py`, `uuid.py`, …) is imported by the launcher instead of the standard library and breaks every start. Reproduced in isolation.
2. **F02** — The environment fast-path fingerprint includes the modification time of `site-packages`. The first import of a top-level module creates `site-packages\__pycache__`, which changes that time. The next start then repeats the full uv check, and if the first instance is still running it is refused with "Close the running app instance(s) first" although nothing has to change.
3. **F03** — Setup sets `core.hooksPath` in every clone whose `origin` is named `PyApp-Template`. The README's Quick start tells app authors to clone, so they get the maintainer hooks, and the setting survives re-pointing `origin`. Those hooks block commits containing an email address and pushes made with a non-`noreply` commit email.
4. **F04** — After a successful no-terminal run, `process_exit.py` runs without a window. If it raises, it calls `input()`, which blocks forever on the hidden console. The watchdog has already unregistered, so the two processes are invisible to Stop. The blocking was reproduced.
5. **F05** — The crash log is written before the traceback is printed. If writing it fails, the app's own error is never shown.
6. **F06** — The dev tools rewrite the `packages` block and silently drop the developer's comments in it. Reproduced.

**Findings by severity**

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 6 |
| Low | 30 |
| Optional | 10 |
| **Total** | **46** |

By confidence: 17 Confirmed, 25 High confidence, 4 Needs verification.

**Areas of greatest concern**

- Process and environment boundaries: `sys.path` ordering, hidden consoles, the environment stamp, per-user folders shared between projects.
- Side effects outside the project folder that the user did not ask for (Git hooks).
- Documentation that trails recent renames (`make_portable`, `dev/`, "Dev Helpers", the shortcut target).

**Highest-value improvements**

- `sys.path.append` instead of `insert(0, …)` in three files (F01) — a one-word change each.
- Drop the `site-packages` directory time from the fingerprint, or refuse only when a change is actually needed (F02).
- Make the Git hooks opt-in, or re-check the remote when a hook runs (F03).
- Never wait for input in a windowless completion handler (F04), and print the report before writing the crash log (F05).

---

## B. Repository overview

**Purpose.** A template that turns a Python script or GUI into a Windows "app" started from shortcuts, without the end user installing Python. [uv](https://docs.astral.sh/uv/) provides the interpreter and locked packages. The launcher adds per-run log files, crash reports, a Stop shortcut, instance policies, a missing-package recovery menu, icon generation and developer tools.

**Architecture.** One start runs through four layers:

```text
shortcut (.lnk, target conhost.exe)
 └─ DC/B/W.bat | N.bat                      sets the launch mode
     └─ DC/bootstrap/run.bat
         ├─ ensure_runtime.bat              cached uv + Python paths (tmp/runtime.cmd)
         │   └─ resolve_runtime.bat/.py     only when the cache is stale
         └─ python -I -S scripts/entrypoint.py actions/start_program.py
             ├─ scripts/env/venv.py         ensure_environment(): .venv matches uv.lock
             └─ runtime/bg_watchdog.py      owns the run (job object, registry, log)
                 ├─ runtime/script_wrapper.py ──▶ code/main.py   (app's .venv Python)
                 └─ runtime/process_exit.py      completion, crash log, recovery
```

**Main components**

| Area | Path | Role |
|---|---|---|
| App (example) | `code/main.py`, `code/settings.py` | Tkinter example and user settings |
| Settings | `code/pyapp/developer_settings.py` | The one file developers edit |
| Bootstrap | `DC/B/*.bat`, `DC/bootstrap/*` | Batch entry points; finds or installs uv and Python |
| Actions | `DC/actions/*.py` | Start, Stop, Setup, open file/folder, icon generation |
| Runtime | `DC/runtime/*.py` | Watchdog, wrapper, completion handler, Ctrl+C helper |
| Shared code | `DC/scripts/**` | Config, console, registry/jobs, shortcuts (COM via ctypes), uv/venv, import finder, dev tools |
| Maintainer tools | `DC/pyapp_tools/**` | Verify (Ruff/Pyrefly), tests on several Pythons, fresh-clone test, leak check, release, Git hooks |
| Tests | `DC/tests/**` | 27 `unittest` files |
| Generated | `code/pyapp/generated/` | `uv.lock`, `.python-version`, icon record (committed); `.venv`, `pyproject.toml`, uv, Pythons (ignored) |

**Languages and technologies.** Python (standard library only inside the launcher), Windows batch, one PowerShell script, GitHub Actions YAML. Windows APIs through `ctypes` (job objects, named mutexes, COM shell links, Toolhelp, console). WPF through `powershell.exe` for icons.

**Supported platforms and versions.** Windows only (x64 documented; ARM64 and x86 uv targets are mapped). Launcher code targets Python 3.8+ (`ruff.toml` `target-version = "py38"`, `pyrefly.toml` `python-version = "3.8"`). The app Python is whatever `python_version` requests; this checkout uses 3.14.

**Entry points**

- `Setup - run first and after moving folder.cmd` → `DC/run.bat setup`
- Shortcuts → `DC/B/{W,N,Q,S,M,L,C,T}.bat`
- `code/pyapp/dev_tools/*.cmd` → `DC/run.bat dev <command>`
- `code/pyapp/icons/*.cmd` → `DC/run.bat icons | icons-help`
- `DC/pyapp_tools/*.bat`, `DC/tests/run_launcher_tests.cmd`
- Git hooks `DC/pyapp_tools/src/git_hooks/{pre-commit,pre-push}`
- Workflows `.github/workflows/pyapp-template-*.yml`

**Dependencies and tooling.** No Python package dependencies in the launcher. External programs: `uv` (0.13.5 on the audit machine), `git`, `conhost.exe`, `cmd.exe`, `wt.exe` (optional), `powershell.exe`, `curl.exe`, `tar.exe`, `certutil.exe` (fallback), VS Code (optional). Tooling: Ruff, Pyrefly, `unittest`.

---

## C. Audit coverage and methodology

**Revision.** `83d5d141` on `dev`, in sync with `origin/dev`.

**Uncommitted changes.** At the start the tree was clean apart from one untracked file, `REPOSITORY_AUDIT_old.md`. **During the audit, changes made by someone else appeared in the working tree** and the untracked file disappeared:

```text
 M code/pyapp/DONT_CHANGE/pyapp_tools/README.md
 M code/pyapp/DONT_CHANGE/pyapp_tools/src/git_hooks/pre-push
 M code/pyapp/DONT_CHANGE/tests/test_imports.py
?? code/pyapp/DONT_CHANGE/pyapp_tools/check_repository.bat
?? code/pyapp/DONT_CHANGE/pyapp_tools/src/check_repository.py
?? code/pyapp/DONT_CHANGE/tests/test_repository_check.py
```

The findings below are about the committed revision. The in-progress files were read once and are commented on only in section M. The test runs happened before these files appeared, which is why they report 261 tests.

**Read in full (line by line)**

- Root: `README.md`, `LICENSE.md`, `.gitignore`, `.gitattributes`, the Setup `.cmd`, the three workflows.
- `code/main.py`, `code/settings.py`, `code/pyapp/developer_settings.py`, `code/pyapp/README.md`, `code/pyapp/.gitignore`, `code/pyapp/generated/*` (tracked files), all `code/pyapp/dev_tools/*.cmd` and its `README.md`, both `code/pyapp/icons/*.cmd`.
- `DC/`: `README.md`, `LICENSE.md`, `ruff.toml`, `pyrefly.toml`, `.gitignore`, `.gitattributes`, `run.bat`, `backend_settings.py`.
- `DC/B/*.bat` (8), `DC/bootstrap/*` (6).
- `DC/actions/*.py` (6), `DC/runtime/*.py` (5).
- `DC/scripts/*.py` (17), `DC/scripts/env/*.py` (5), `DC/scripts/dev_tools/*.py` (7).
- `DC/pyapp_tools/README.md`, `DC/pyapp_tools/src/*.py` (11), `get_longest_paths.ps1`, both Git hooks, and the nine `.bat` wrappers (five read; the other four compared and found identical to those apart from the script name).
- `DC/data/icons/HOW_TO_CHANGE_ICONS.txt`, `DC/data/workflows/leaks.yml`.
- `DC/tests/README.md`, `run_launcher_tests.cmd`, `run_regressions.py`, `support.py`, `project_location.py`.

**Read in part**

- `DC/tests/test_*.py` (27 files, about 200 KB): all test names, platform guards and skips, plus the bodies relevant to findings (`test_packages.py` 215–262, `test_annotations.py`). Not read line by line.
- `DC/CHANGELOG.md` (1,070 lines): headings and the first 40 lines.
- `DC/TODO.md` (1,084 lines): the first 25 lines and keyword searches.
- `DC/data/dev_settings_default.py`: compared byte for byte with `developer_settings.py` (identical), not read separately.
- `DC/data/fonts/pyapp-grid.tlf`: header only.

**Excluded, with reasons**

| Path | Reason |
|---|---|
| `DC/data/import_to_package.txt` (90 KB) | Generated data |
| `DC/LICENSES/*.txt` | Standard license texts |
| `*.png`, `*.ico`, `*.lnk` | Binary assets (record hashes of the `.ico` files were checked) |
| `code/pyapp/generated/.venv`, `uv.lock` body | Generated; third-party |
| `DC/tmp/`, `__pycache__`, `.ruff_cache`, `logs/`, `crash logs/`, `.vscode/` | Ignored runtime state |

**Tools and commands executed**

| Tool | Command (working directory `DC/` unless noted) | Result |
|---|---|---|
| Ruff 0.17.4 (bundled with the VS Code extension `charliermarsh.ruff-2026.94.0`) | `ruff check --no-cache --no-fix --output-format concise .` | All checks passed |
| | `ruff format --no-cache --check .` | 91 files already formatted |
| | `ruff check --no-cache --isolated` on `code/main.py`, `code/settings.py`, `developer_settings.py` (Ruff defaults; no project config applies there) | All checks passed |
| Pyrefly 1.4.1 (bundled with `meta.pyrefly-1.4.1`) | `pyrefly check` | 0 errors (7 suppressed) |
| Tests, Python 3.14.9 | `python -B -X utf8 run_regressions.py -q -j 0` in `DC/tests` | Ran 261 tests in 6.07 s — OK |
| Tests, Python 3.8.20 (already present in `%TEMP%\pyapp_test_pythons`) | same | Ran 261 tests in 5.89 s — OK |
| uv 0.13.5 | `uv python install --help`, `uv pip install --help`, `uv --help`, `uv venv --help` | Confirmed `--upgrade`, `UV_SYSTEM_CERTS`, `UV_WORKING_DIR`, `--relocatable`, `--allow-existing` exist |
| git | `status`, `log`, `ls-files`, `ls-files --eol`, `ls-files --cached --ignored --exclude-standard`, `grep`, `diff` | No tracked-but-ignored files; no mixed line endings |
| GitHub API (public) | releases of `actions/checkout` and `astral-sh/setup-uv` | `v7.0.1` and `v10.3.3` exist |
| Probe scripts (written to the session's scratch folder, outside the repository) | Imported launcher modules read-only and exercised them on temporary folders | See "Evidence" of F01, F04, F06, F08, F09, F10, F28 |

The checker configuration used was exactly the project's: `DC/ruff.toml` (py38, line length 120, the listed `extend-select` groups and ignores) and `DC/pyrefly.toml` (`preset = "strict"`, Python 3.8, Windows, three extra error kinds). Neither tool is installed on `PATH` on the audit machine; the copies bundled with the editor extensions were used. Nothing was installed.

**Not executed**

- Setup, a real app start, Stop, the dev tools, icon generation, the fresh-clone test, `test_all_pythons`, `release`, the Git hooks. They install software, create shortcuts or change settings.
- No end-to-end reproduction of F02, F03 or F05; they are established from the code path plus an isolated check of the mechanism where one exists.

**Limitations**

- Windows-API behavior was reasoned from documentation and the code, not traced with a debugger.
- Findings marked "Needs verification" depend on runtime behavior of uv, Windows Terminal or antivirus software that was not exercised.
- Running the tests left the repository's tracked files untouched; they create temporary folders (see F29).
- The repository changed under the audit (see above). Line numbers are for the committed revision.

---

## D. Prioritized findings summary

| ID | Severity | Confidence | Category | File / Location | Finding |
|---|---|---|---|---|---|
| F01 | Medium | Confirmed | Bug, robustness | `DC/scripts/entrypoint.py:19`, `DC/runtime/bg_watchdog.py:18`, `DC/runtime/process_exit.py:30` | App modules shadow the standard library inside the launcher |
| F02 | Medium | High confidence | Bug, reliability | `DC/scripts/env/venv.py:282, 341` | Fast-path fingerprint changes after the first run; second instance refused |
| F03 | Medium | High confidence | Design, side effect | `DC/scripts/template_repo.py:46-62`, `DC/actions/setup.py:100-107` | Setup enables maintainer Git hooks for app authors who clone |
| F04 | Medium | Confirmed | Bug, resource leak | `DC/runtime/bg_watchdog.py:141-144`, `DC/runtime/process_exit.py:26, 402-408` | Windowless completion handler can block forever on `input()` |
| F05 | Medium | High confidence | Bug, error handling | `DC/runtime/process_exit.py:292-300` | A crash-log write error hides the app's traceback |
| F06 | Medium | Confirmed | Bug, data loss | `DC/scripts/config.py:454-470` | Dev tools drop comments from the `packages` block |
| F07 | Low | High confidence | Bug | `DC/scripts/launcher_ui.py:69` | `terminal_bg_color` alone sets the text color; equal colors are ignored |
| F08 | Low | Confirmed | Bug | `DC/scripts/file_tools.py:13-21` | `remove_tree_inside` raises for a junction that leads outside |
| F09 | Low | Confirmed | Bug | `DC/scripts/diagnostics.py:41-51` | `diagnostics_summary` miscounts chained tracebacks |
| F10 | Low | Confirmed | Bug, validation | `DC/scripts/config.py:342-346`, `DC/bootstrap/resolve_runtime.py:165-171` | `uv_version` accepts values that crash the bootstrap |
| F11 | Low | Confirmed | Documentation, messages | `DC/bootstrap/resolve_runtime.bat:132, 140, 144, 215` | Error messages name the removed `make_portable` tool |
| F12 | Low | High confidence | Resource use | `DC/bootstrap/resolve_runtime.py:284-294` | The local uv folder keeps the downloaded archive |
| F13 | Low | Needs verification | Concurrency | `DC/bootstrap/resolve_runtime.bat:101-103`, `resolve_runtime.py:42-44` | Per-user uv folders are shared without a shared lock |
| F14 | Low | High confidence | Consistency | `DC/scripts/env/uv.py:58-75`, `resolve_runtime.py:50-62`, `resolve_runtime.bat:158-177` | Three copies of the uv environment rules have drifted |
| F15 | Low | High confidence | Robustness | `DC/scripts/runtime_state.py:234-250` | A read error deletes the record of a running instance |
| F16 | Low | Needs verification | Robustness | `DC/scripts/windows_focus.py:34-59` | Process tree trusts parent PIDs without checking creation time |
| F17 | Low | High confidence | Correctness (FFI) | `DC/scripts/com_tools.py:41-50` | `PROPVARIANT` is smaller than the Windows structure |
| F18 | Low | Needs verification | Bug | `DC/scripts/env/venv.py:273, 285-313` | Loose `python_version` requests can leave the lock unused for good |
| F19 | Low | High confidence | Data loss | `DC/scripts/env/pyproject.py:127-146` | Dependency groups from `uv add --dev` are dropped without a word |
| F20 | Low | High confidence | Bug (configuration) | `DC/scripts/dev_tools/packages.py:190-205` | `export_requirements` can overwrite the file `requirements_path` reads |
| F21 | Low | Confirmed | Bug, messages | `DC/scripts/dev_tools/housekeeping.py:130-137` | `clean` reports deleting diagnostics it kept |
| F22 | Low | High confidence | Robustness | `DC/scripts/dev_tools/housekeeping.py:148-149`, `DC/actions/setup.py:118-140` | The shortcut record is lost on partial failure |
| F23 | Low | High confidence | Robustness | `DC/scripts/dev_tools/housekeeping.py:157-193` | `status` aborts on an unreadable requirements file |
| F24 | Low | High confidence | Race condition | `DC/actions/start_program.py:136-148` | Start can misreport a cancelled launch as a failed one |
| F25 | Low | Needs verification | Bug | `DC/actions/start_program.py:115-122` | `;` in the program name or path is not escaped for `wt.exe` |
| F26 | Low | Confirmed | Dead code, documentation | `DC/scripts/shortcuts.py:82-83, 198, 233` | `classic_terminal=False` is never used; docs describe the wrong target |
| F27 | Low | Confirmed | Documentation | `DC/README.md:325-340`, `DC/tests/README.md:16-33` | File tables trail renames; 11 test files are not listed |
| F28 | Low | Confirmed | Typing, convention | `DC/scripts/image_tools.py:6, 74` | Annotation breaks `typing.get_type_hints()` on Python 3.8 |
| F29 | Low | Confirmed | Tests | `DC/tests/project_location.py:19` | Every test process leaks a temporary folder |
| F30 | Low | High confidence | Messages | `DC/bootstrap/resolve_runtime.py:405-418` | A blocked uv is reported as an outdated one |
| F31 | Low | High confidence | Robustness | `DC/bootstrap/resolve_runtime.py:352-362` | PATH entry comparison is exact text |
| F32 | Low | High confidence | Error handling | `resolve_runtime.py:486-496`, `DC/scripts/env/pythons.py:22-30`, `bg_watchdog.py:189-201` | Probe and cleanup steps can end in a raw traceback |
| F33 | Low | High confidence | Security tooling | `DC/pyapp_tools/src/check_git_leaks.py:170-171, 196-198` | Leak check skips UTF-16 text and loads the whole history |
| F34 | Low | Confirmed | Repository hygiene | `DC/TODO.md` | 1,084 lines of working notes ship with the launcher |
| F35 | Low | High confidence | Design | `DC/actions/setup.py:110-112` | Copies with the same program name overwrite each other's shortcuts |
| F36 | Low | Confirmed | Spelling | `code/pyapp/developer_settings.py:13` (and its copy) | "compatibitly" |
| F37 | Optional | Confirmed | Input handling | five menus | `str.isdigit()` accepts text `int()` rejects |
| F38 | Optional | High confidence | Hardening | several | System programs are started by bare name |
| F39 | Optional | High confidence | Efficiency | `resolve_runtime.py:446-457` | A newer uv is fetched for any Python install failure |
| F40 | Optional | High confidence | Cosmetic | `DC/scripts/console_tools.py:154, 309` | Restoring the console also un-maximizes it; title keeps `\n` |
| F41 | Optional | High confidence | Messages | `DC/scripts/runtime_state.py:578-591` | Only five crash codes are recognized |
| F42 | Optional | High confidence | Usability | `DC/scripts/import_finder.py:69-80` | Import finder scans environments not named with a dot |
| F43 | Optional | Confirmed | CI | `.github/workflows/*.yml` | No CI on `dev`; actions pinned by tag |
| F44 | Optional | High confidence | Performance | `DC/runtime/script_wrapper.py:108-137`, `process_exit.py:130-140` | Per-write overhead; crash logs copy the whole log |
| F45 | Optional | High confidence | Configuration | `bg_watchdog.py:316-323`, `start_program.py:135` | Fixed start-up timeouts |
| F46 | Optional | Confirmed | Maintainability | `DC/pyapp_tools/*.bat`, `resolve_runtime.py:151-152` | Seven identical wrappers; small redundancies |

---

## E. Detailed findings

### F01 — App modules shadow the standard library inside the launcher

- **Severity / Confidence / Category:** Medium · Confirmed (mechanism reproduced in isolation) · Bug, robustness
- **Location:** `DC/scripts/entrypoint.py:19`, `DC/runtime/bg_watchdog.py:18`, `DC/runtime/process_exit.py:30`
- **Current behavior:** Each launcher process starts with `python -I -S` and then makes the `code` folder importable with `sys.path.insert(0, …)`, so that `pyapp.DONT_CHANGE…` resolves.
- **Problem:** Position 0 comes before the standard library. The launcher imports most modules lazily (the Ruff config allows `PLC0415` for exactly that reason), so any standard-library module first imported *after* that line is looked up in the app's folder first.
- **Evidence:**
  ```python
  # entrypoint.py:17-19
  if __name__ == "__main__":
      # -I leaves the script folder off sys.path; make "pyapp...." importable (the code folder).
      sys.path.insert(
          0,
          os.path.normpath(str((Path(__file__).parent / ".." / ".." / "..").absolute())),
      )
  ```
  Isolated check with a folder containing `uuid.py`: `python -I -S -c "sys.path.insert(0, d); import uuid"` raised the app module's error; with `sys.path.append(d)` the standard-library `uuid` was imported. In the launcher, `start_program.py` imports `subprocess`, `shutil`, `uuid`, `json` and (through `scripts/env/pythons.py`) `tempfile` after the insert. `tempfile` imports `random`; `subprocess` imports `signal`. A second check imported exactly what `entrypoint.py` imports before line 19 and listed what is still missing from `sys.modules` at that point, on 3.8.20 and 3.14.9: `random`, `signal`, `json`, `uuid`, `tempfile`, `subprocess`, `shutil`, `hashlib`, `datetime`, `struct`, `threading`, `ctypes`, `email`, `string`, `queue`, `platform` (and on 3.8 also `ast` and `copy`).
- **Impact:** An app that has, for example, `code/random.py`, `code/signal.py`, `code/json.py` or `code/uuid.py` cannot be started: the launcher fails with a traceback that points into the app's file, running app code in the package-less launcher interpreter. This contradicts the README's "your packages can't break it". `signal.py` is a plausible name in scientific code.
- **Recommendation:** Append instead of insert. `pyapp` is not a standard-library name, so the launcher's own imports still resolve.
- **Example:**
  ```python
  sys.path.append(
      os.path.normpath(str((Path(__file__).parent / ".." / ".." / "..").absolute()))
  )
  ```
- **Verification:** Add a test that creates a temporary project with `code/random.py` raising on import and runs `entrypoint.py` with a trivial tool; it must exit 0. `tests/test_wrapper.py` already has the mirror-image test for the app side (`test_apps_own_protocol_module_is_not_shadowed`).

### F02 — Fast-path fingerprint changes after the first run; second instance refused

- **Severity / Confidence / Category:** Medium · High confidence (mechanism confirmed; not run end to end) · Bug, reliability
- **Location:** `DC/scripts/env/venv.py:277-283` (use), `317-348` (fingerprint, `site-packages` at line 341)
- **Current behavior:** `ensure_environment()` returns early when `tmp/environment.ok` equals a hash that includes time and size of `…\.venv\Lib\site-packages`. On a mismatch it first calls `refuse_mutation_while_running()`, then runs the uv checks and writes a new stamp.
- **Problem:** uv does not compile bytecode on install. The first time the app imports a module that lives directly in `site-packages` (`six.py`, `typing_extensions.py`, …), Python creates `site-packages\__pycache__`, which changes the directory's modification time. The stamp written by Setup therefore stops matching after the first run although nothing relevant changed.
- **Evidence:**
  ```python
  # venv.py:278-283
  if _read_stamp() == fingerprint:
      return AppPython(VENV_PYTHON_EXE, APP_PYTHON_FLAGS)
  # From here on the environment may be synced or rebuilt, ...
  refuse_mutation_while_running()
  ```
  Probe: a folder with one module, imported once with `-E -s` → `__pycache__ created: True | dir mtime changed: True`. The test `test_a_launch_does_not_sync_under_a_running_instance` states the intent: "An unchanged environment is not touched, so a second instance can still start."
- **Impact:** (a) After Setup or any package change, the second start repeats `uv lock --check` and `uv sync` once (noticeably slower). (b) With the default `instance_policy = "allow"`, starting a second instance while that first one runs fails with "Close the running app instance(s) first; they use the files in the Python environment." The same applies to Setup and the dev tools.
- **Recommendation:** Remove the `site-packages` entry from the fingerprint, or stat the `.dist-info` folder names instead of the directory time. Independently, call `refuse_mutation_while_running()` only when a step is about to change something (lock out of date, sync reports changes, venv must be rebuilt).
- **Verification:** Test: build a fingerprint, create `site-packages/__pycache__`, assert the fingerprint is unchanged, then add a `x.dist-info` folder and assert it changed. Manual: Setup, start, start again while running.

### F03 — Setup enables maintainer Git hooks for app authors who clone

- **Severity / Confidence / Category:** Medium · High confidence · Design, unrequested side effect
- **Location:** `DC/scripts/template_repo.py:46-62`, `DC/actions/setup.py:100-107`, `README.md:60`, `DC/pyapp_tools/README.md` (hooks row), `DC/CHANGELOG.md` ("never in an app built from it")
- **Current behavior:** Setup runs `git config --local core.hooksPath code/pyapp/DONT_CHANGE/pyapp_tools/src/git_hooks` when the folder is a Git repository, `origin` ends in `/PyApp-Template` and no hooks path is set. It prints a "Git hooks" heading when it does.
- **Problem:** The test "is this the template itself" is the remote name at the moment Setup runs. The Quick start says "Clone or download this repository", so an app author's first Setup runs in exactly such a clone. The setting is local and persistent; changing `origin` to the app's own repository later does not remove it.
- **Evidence:**
  ```python
  remote = run(["remote", "get-url", "origin"])
  if not remote or not TEMPLATE_REMOTE.search(remote):
      return False
  if run(["config", "--local", "--get", "core.hooksPath"]):
      return False
  return run(["config", "--local", "core.hooksPath", HOOKS_PATH]) is not None
  ```
  The hooks then run `check_git_leaks.py --committing` (stops a commit for any email address or home-folder path in staged lines) and, on push, `--pushing` (stops a push when a commit's author email is not a `noreply` address), followed by `verify_launcher` and the launcher tests.
- **Impact:** App authors get commits and pushes blocked by checks they did not ask for and that concern the template, with about 20 s added to every push. The documentation says this cannot happen.
- **Recommendation:** Prefer explicit opt-in (a line in the maintainer documentation, or a `pyapp_tools/enable_hooks.bat`). If the convenience should stay, let the hooks themselves exit 0 when `git remote get-url origin` no longer names the template, and mention the hooks in the Quick start.
- **Verification:** Clone the template, run Setup, `git remote set-url origin <other>`, commit a file containing an email address: the commit must succeed.

### F04 — Windowless completion handler can block forever on `input()`

- **Severity / Confidence / Category:** Medium · Confirmed (blocking reproduced; trigger by code path) · Bug, resource leak
- **Location:** `DC/runtime/bg_watchdog.py:141-144` and `362`; `DC/runtime/process_exit.py:19-27`, `307-308`, `402-408`; `DC/scripts/console_tools.py:107-110`
- **Current behavior:** After a successful no-terminal run with `close_after_success = True`, the watchdog runs `process_exit.py` with `CREATE_NO_WINDOW` and waits for it. If `process_exit.py` raises, its top-level handler prints the traceback and calls `wait_for_enter()`; an import failure calls `input()` directly.
- **Problem:** `CREATE_NO_WINDOW` gives the child a console without a window. `input()` reads from it and never returns, and nobody can type into it. `wait_for_enter()` only suppresses `EOFError` and `KeyboardInterrupt`.
- **Evidence:** Probe that starts a parent the way `start_program.py` starts a no-terminal watchdog (`CREATE_NO_WINDOW`, stdout and stderr to a file) and a child the way `handle_exit` does: `child BLOCKED on input() for 8 s (killed by the probe)`. The registration is removed before the handler runs:
  ```python
  # bg_watchdog.py:361-364
  registry.remove()
  registered = False
  exit_handled = True
  ```
- **Impact:** Two Python processes (watchdog and handler) stay alive invisibly, and Stop cannot find them. A realistic trigger: `developer_settings.py` is edited into an invalid state while the app runs, so `settings()` in `process_exit.main()` (line 308) raises when the app ends.
- **Recommendation:** Tell the handler that it has no window (it already receives that as an argument) and skip every prompt in that case; better, re-run the handler in a visible console when the hidden one fails, so the error is seen.
- **Example:**
  ```python
  # process_exit.py, top-level handler
  except Exception as error:
      print_traceback(fail_message.format(e=error))
      if console_is_visible():      # e.g. ctypes IsWindowVisible(GetConsoleWindow())
          wait_for_enter()
      sys.exit(1)
  ```
  and in `handle_exit`: if the hidden run returns non-zero, start it again through `conhost.exe` with `CREATE_NEW_CONSOLE`.
- **Verification:** Test that runs `process_exit.py` with `CREATE_NO_WINDOW`, an invalid exit mode and a timeout; it must exit instead of timing out.

### F05 — A crash-log write error hides the app's traceback

- **Severity / Confidence / Category:** Medium · High confidence · Bug, error handling
- **Location:** `DC/runtime/process_exit.py:292-300` (`complete`), `143-164` (`write_crash_log`)
- **Current behavior:** For every outcome other than success, `complete()` writes the crash log and only afterwards prints the report.
- **Problem:** `write_crash_log` creates folders and opens the file without catching `OSError`. A `crash_log_path` on a missing drive, a read-only or full disk, or a date code that produces an invalid file name (`%c` contains `:`) raises. The exception leaves `complete()` before `print_report(report)` runs.
- **Evidence:**
  ```python
  if outcome != "success":
      crash_log = write_crash_log(report, message, log_path)  # may raise OSError
      ...
  print_report(report)  # not reached
  ```
- **Impact:** The window shows "Failed while processing program exit: …" with a launcher traceback. The reason the app failed, the one thing the window exists for, is not shown and not saved.
- **Recommendation:** Print the report first, then write the crash log inside `try/except OSError` and report the problem as one error line. `append_printed_output` already follows that pattern.
- **Verification:** Test with `crash_log_path` pointing below an existing *file*; the rendered report must still be in the output.

### F06 — Dev tools drop comments from the `packages` block

- **Severity / Confidence / Category:** Medium · Confirmed · Bug, data loss
- **Location:** `DC/scripts/config.py:454-470` (`set_list_setting`), callers `DC/scripts/env/pyproject.py:116` and `249-253`
- **Current behavior:** When `packages` is a triple-quoted block, `set_list_setting` rewrites it from the parsed entries. `parse_requirements` strips comments, blank lines and `--hash` options, so they are gone after any `add_packages`, `remove_packages`, `find_imports` or copy-back from `uv add`.
- **Problem:** The docstring promises the opposite: "A setting written as a triple-quoted block stays one, so a pasted requirements list keeps its form." The settings comment invites comments ("# comments and --hash options are fine"). The diff that `set_list_setting` returns is discarded by `reconcile_pyproject`, so the user is not told.
- **Evidence:** Probe on a temporary copy of the settings file:
  ```text
  - packages: Union[List[str], str] = """
  - # GUI
  - requests>=2  # pinned because of the proxy bug
  -
  - # numerics
  - numpy>=2
  - """
  + packages: Union[List[str], str] = """
  + requests>=2
  + numpy>=2
  + pillow
  + """
  ```
- **Impact:** Developer notes about why a package is pinned disappear from the one file the template asks people to edit. Hash pins in the block are removed too (the lock file still has hashes).
- **Recommendation:** Edit the block line by line: keep every existing line whose requirement is still wanted (with its comment), delete lines of removed requirements, append new ones. At minimum, print the diff and fix the docstring.
- **Verification:** Extend `tests/test_settings.py` (editing settings) with a block that has full-line and trailing comments; after adding one package, all comments must still be there.

### F07 — `terminal_bg_color` alone sets the text color; equal colors are ignored

- **Severity / Confidence / Category:** Low · High confidence (per the documented behavior of `color`; not executed) · Bug
- **Location:** `DC/scripts/launcher_ui.py:66-69`, `DC/scripts/console_tools.py:380-393`, `DC/scripts/config.py:396-401`, `code/pyapp/developer_settings.py:114-117`
- **Current behavior:** `set_settings_colors` concatenates `(bg or "") + (text or "")` and passes the result to `cmd /c color`.
- **Problem:** Both settings may be `None`. With `terminal_bg_color = "9"` and `terminal_text_color = None` the argument is `9`, and `color` treats a single digit as the *foreground*. With equal digits `color` does nothing and returns error level 1, which is neither validated nor noted.
- **Evidence:** `_set_terminal_colors((s.terminal_bg_color or "") + (s.terminal_text_color or ""))`. `color /?`: the attribute is two hex digits, background first.
- **Impact:** A developer who only wants a blue background gets blue text on black.
- **Recommendation:** Fill the missing half with the console default (`0` background, `7` text), and report equal values in `validate()`.
- **Example:** `colors = (s.terminal_bg_color or "0") + (s.terminal_text_color or "7")` when at least one is set.
- **Verification:** Unit test on the string passed to `set_terminal_colors`; validation test for `"9"`/`"9"`.

### F08 — `remove_tree_inside` raises for a junction that leads outside

- **Severity / Confidence / Category:** Low · Confirmed · Bug
- **Location:** `DC/scripts/file_tools.py:9-22`
- **Current behavior:** The function resolves `path` with `os.path.realpath` and compares the result with `base`. Only afterwards does it check whether `path` itself is a link.
- **Problem:** `realpath` follows junctions and symlinks. For a link inside `base` whose target is elsewhere, the containment check fails and `ValueError` is raised before the link branch (lines 19–21) is reached. That branch only runs for links that point back into `base`.
- **Evidence:** Probe: junction `base\link` → `outside` gives `ValueError: Refusing to delete … it is not inside …`; the link stays. A junction to a folder inside `base` is removed correctly.
- **Impact:** Limited: the two callers (`tmp/runs` clean-up) normally see no links. In `delete_finished_run_folders` the `ValueError` is not an `OSError`, so one such entry stops the clean-up of all remaining run folders (the outer handler records it).
- **Recommendation:** Check the link first, on the unresolved path, and compare the unresolved absolute path with `base` for containment.
- **Example:**
  ```python
  absolute = os.path.abspath(path)
  if not _inside(absolute, os.path.realpath(base)):
      raise ValueError(...)
  if Path(absolute).is_symlink() or _is_junction(absolute):
      os.rmdir(absolute) if os.path.isdir(absolute) else os.unlink(absolute)
      return
  shutil.rmtree(absolute)
  ```
- **Verification:** Windows-only test with `mklink /J`; the link must be gone and the target intact.

### F09 — `diagnostics_summary` miscounts chained tracebacks

- **Severity / Confidence / Category:** Low · Confirmed · Bug
- **Location:** `DC/scripts/diagnostics.py:41-51`
- **Current behavior:** Entries are separated by a blank line and counted by splitting the file at `"\n\n"`.
- **Problem:** `traceback.format_exc()` of a chained exception contains blank lines around "During handling of the above exception, another exception occurred:".
- **Evidence:** Probe with one chained entry: `3 ignored error(s), last: Traceback (most recent call last):`.
- **Impact:** The `status` tool shows an inflated count and a meaningless "last" line.
- **Recommendation:** Count header lines instead, e.g. lines matching `^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  pid \d+  `, and show the last such line.
- **Verification:** Extend `test_ignored_errors_are_recorded` with a chained exception.

### F10 — `uv_version` accepts values that crash the bootstrap

- **Severity / Confidence / Category:** Low · Confirmed · Bug, validation
- **Location:** `DC/scripts/config.py:342-346`; `DC/bootstrap/resolve_runtime.py:165-171, 185-189`
- **Current behavior:** Validation accepts any text made of `[0-9.,<>=!~ ]`. The bootstrap parses each clause with `([0-9][0-9.]*)` and converts the parts with `int()`.
- **Problem:** `">=0..9"` passes both regular expressions and then fails in `int("")`. The bootstrap runs before validation, so the user sees a traceback and "Preparing uv and Python failed: invalid literal for int()".
- **Evidence:** Probe: `resolve_runtime.version_satisfies("0.11.2", ">=0..9")` → `ValueError: invalid literal for int() with base 10: ''`.
- **Impact:** A typo in `uv_version` produces an unhelpful error on every start.
- **Recommendation:** Use one stricter pattern in both places, `\d+(\.\d+)*`, and raise `BootstrapError` for anything else.
- **Verification:** Add the case to `test_a_clause_that_makes_no_sense_is_reported` and to the settings validation tests.

### F11 — Error messages name the removed `make_portable` tool

- **Severity / Confidence / Category:** Low · Confirmed · Documentation, messages
- **Location:** `DC/bootstrap/resolve_runtime.bat:132, 140, 144, 215`
- **Current behavior:** Four bootstrap error messages end with "copy a folder made with the make_portable dev tool to this PC".
- **Problem:** The tool was renamed to `make_self_contained` (changelog; `resolve_runtime.py:243, 581` already use the new name). `dev_tools/main.py` has no `make_portable` command.
- **Impact:** Users on a blocked network, the audience of these messages, are pointed to a tool that does not exist.
- **Recommendation:** Replace the name in the four lines. Consider a test that greps the launcher for retired names.
- **Verification:** `git grep make_portable -- code` returns only changelog and TODO lines.

### F12 — The local uv folder keeps the downloaded archive

- **Severity / Confidence / Category:** Low · High confidence · Resource use
- **Location:** `DC/bootstrap/resolve_runtime.py:284-294`, `332-337`; `DC/bootstrap/resolve_runtime.bat:101-124`
- **Current behavior:** The batch stage downloads `uv-<target>.zip` and its `.sha256` into `%LOCALAPPDATA%\PyApp-Template\uv-bootstrap`, unpacks them there and does not delete the archive. `fetch_uv_folder` copies that whole folder, and `install_uv` renames the copy to the destination.
- **Problem:** For a local install (`uv_install_if_missing = "local"`), `code/pyapp/generated/uv` then contains the zip and checksum next to `uv.exe`. The global install copies only `*.exe` and is not affected.
- **Evidence:** `shutil.copytree(str(Path(bootstrap_uv).parent), str(extracted))`.
- **Impact:** Roughly 20–25 MB of dead weight in a folder that is meant to be zipped and handed over.
- **Recommendation:** Delete the archive and checksum in the batch stage after unpacking, or copy only `*.exe` in `fetch_uv_folder`.
- **Verification:** Unit test for `fetch_uv_folder` with a fake bootstrap folder; the result holds no `.zip`.

### F13 — Per-user uv folders are shared without a shared lock

- **Severity / Confidence / Category:** Low · Needs verification · Concurrency
- **Location:** `DC/bootstrap/resolve_runtime.bat:101-103`; `DC/bootstrap/resolve_runtime.py:42-44, 446-457, 622-641`
- **Current behavior:** `uv-bootstrap` and the shared `uv` folder live under `%LOCALAPPDATA%\PyApp-Template` and are used by every project. The only lock is `DC/tmp/bootstrap.lock`, which is per project and taken only by the Python stage.
- **Problem:** Two first starts at the same time (two projects, or one project started twice before the cache exists) both run `rmdir /s /q` + download + `tar` in the same folder; two projects can replace the shared uv at once.
- **Impact:** A failed first start with a checksum or unpack error; a retry works.
- **Recommendation:** Download into a unique folder (`uv-bootstrap-%RANDOM%`) and take a lock file next to the shared uv in `install_uv`.
- **Verification:** Start Setup in two fresh copies simultaneously on a PC without uv.

### F14 — Three copies of the uv environment rules have drifted

- **Severity / Confidence / Category:** Low · High confidence · Consistency
- **Location:** `DC/scripts/env/uv.py:58-75` and `78-120`; `DC/bootstrap/resolve_runtime.py:50-62, 463-483`; `DC/bootstrap/resolve_runtime.bat:158-177`
- **Current behavior:** Both Python files say they mirror each other; the batch file has its own list.
- **Problem:** The launcher removes `UV_NO_SYNC`, `UV_FROZEN`, `UV_LOCKED`, `UV_OFFLINE`, `UV_CACHE_DIR` and `UV_PYTHON_DOWNLOADS` from the user's environment; the bootstrap does not. A user-level `UV_OFFLINE=1` therefore fails the bootstrap's Python install but is ignored later, and a user `UV_CACHE_DIR` is honored by the bootstrap and dropped by the launcher. The batch stage treats a missing `uv_user_python_visible_globally` as "not visible" while both Python stages default to `True`.
- **Impact:** Hard-to-explain differences between the first start and later ones on PCs with uv variables set.
- **Recommendation:** Make the two Python lists identical and add a test that compares them (the tests already compare the bootstrap defaults). Decide and document whether a user's `UV_CACHE_DIR` should win when `uv_cache = "global"`.
- **Verification:** A test asserting `set(resolve_runtime.OWN_UV_VARIABLES) == set(uv._OWN_UV_VARIABLES)` or a documented difference.

### F15 — A read error deletes the record of a running instance

- **Severity / Confidence / Category:** Low · High confidence (code path); the trigger needs outside interference · Robustness
- **Location:** `DC/scripts/runtime_state.py:234-250`
- **Current behavior:** `_records` treats every `OSError`, `ValueError`, `KeyError` or `TypeError` while reading a record as "stale" and deletes the file. The `unlink` is outside the `try`.
- **Problem:** A sharing violation from antivirus or an indexer is also an `OSError`. The record of a live instance is then removed, or, if the delete fails too, `PermissionError` leaves `records()`.
- **Impact:** The instance becomes invisible to Stop and to `instance_policy`; or a launch ends with a traceback.
- **Recommendation:** Treat only `FileNotFoundError` and parse errors as stale; skip the record for other `OSError`s; wrap the `unlink` in `contextlib.suppress(OSError)`.
- **Verification:** Test with `Path.read_text` patched to raise `PermissionError`: the file must remain.

### F16 — Process tree trusts parent PIDs without checking creation time

- **Severity / Confidence / Category:** Low · Needs verification · Robustness
- **Location:** `DC/scripts/windows_focus.py:34-59`; users `DC/scripts/runtime_state.py:369-373, 534-560`, `windows_focus.py:105-108`
- **Current behavior:** `process_tree` builds parent→children from a Toolhelp snapshot.
- **Problem:** Windows does not update `th32ParentProcessID` when a parent exits, and PIDs are reused. A process whose long-dead parent had the PID the watchdog now has is counted as its child.
- **Impact:** Only on fallback paths (no usable job object): `terminate_tree` could end an unrelated process, the `WM_CLOSE` fallback could close an unrelated window, `focus` could raise the wrong window.
- **Recommendation:** Accept a child only if its creation time is later than its parent's (`GetProcessTimes`, already used in `process_identity`).
- **Verification:** Unit test on a fake snapshot with injected creation times.

### F17 — `PROPVARIANT` is smaller than the Windows structure

- **Severity / Confidence / Category:** Low · High confidence · Correctness (FFI)
- **Location:** `DC/scripts/com_tools.py:41-50`
- **Current behavior:** The structure has four 16-bit fields and one pointer: 16 bytes on x64, 12 on x86.
- **Problem:** The Windows `PROPVARIANT` is 24 bytes on x64 and 16 on x86. `IPropertyStore::SetValue` receives a pointer to a shorter buffer; an implementation that copies the whole structure reads 8 bytes past it.
- **Impact:** Works in practice because only the pointer is used for `VT_LPWSTR`; formally an out-of-bounds read.
- **Recommendation:** Add a padding field (`("padding", ctypes.c_void_p)`) so the size matches.
- **Verification:** `assert ctypes.sizeof(PROPVARIANT) == (24 if ctypes.sizeof(ctypes.c_void_p) == 8 else 16)` in a Windows test.

### F18 — Loose `python_version` requests can leave the lock unused for good

- **Severity / Confidence / Category:** Low · Needs verification (depends on which interpreter uv returns for a loose request) · Bug
- **Location:** `DC/scripts/env/venv.py:273, 285-313`; `DC/scripts/env/pythons.py:146-152`
- **Current behavior:** `requires-python` is written once as `==X.Y.*` and afterwards kept (`reconcile_pyproject(s, None if current_requires_python() else base_version)`). When the launcher Python's minor version is outside it, the environment is installed without the lock and no stamp is written.
- **Problem:** A request such as `"3"`, `">=3.12"` or `"pypy"` stays equal between the setting and `.python-version`, so the migration menu never appears. If uv later resolves that request to a newer minor version, every start prints the "outside requires-python" warning, rebuilds or `pip install`s without the lock, and takes the slow path, with no way out except `change_python`.
- **Evidence:** `locked = version_satisfies_requires(base_version, current_requires_python())` … `if locked: _write_stamp(...)`.
- **Impact:** Unreproducible package versions and slow starts after a Python minor release, for projects that use a loose request. `python_version = ""` is not affected (the launcher records "X.Y").
- **Recommendation:** When the minor version differs and the setting matches the file, treat it like a version change: offer the migration menu, or record the resolved "X.Y" in `.python-version` on the first run for every request form.
- **Verification:** With two managed Pythons installed, set `python_version = "3"`, run Setup, install the newer minor, start again.

### F19 — Dependency groups from `uv add --dev` are dropped without a word

- **Severity / Confidence / Category:** Low · High confidence · Data loss
- **Location:** `DC/scripts/env/pyproject.py:127-146`
- **Current behavior:** `pyproject.toml` is regenerated from a fixed template whenever its text differs. A warning is printed only for `[tool.uv.sources]`.
- **Problem:** `uv add --dev pytest` or `uv add --optional …` in the package terminal writes `[dependency-groups]` or `[project.optional-dependencies]`. `[project] dependencies` is unchanged, so nothing is copied back, and the next start overwrites the file.
- **Impact:** The developer's dev dependencies vanish on the next start and get uninstalled by the next exact sync.
- **Recommendation:** Extend `_warn_about_dropped_sources` to these tables, and say in the package terminal's help that only plain `uv add` is recorded.
- **Verification:** Extend `test_dropped_package_sources_are_reported` with a `[dependency-groups]` table.

### F20 — `export_requirements` can overwrite the file `requirements_path` reads

- **Severity / Confidence / Category:** Low · High confidence (needs a specific setting) · Bug
- **Location:** `DC/scripts/dev_tools/packages.py:190-205`; `DC/backend_settings.py:125`; `DC/scripts/config.py:146-152`
- **Current behavior:** The export always writes `code/pyapp/requirements.txt`. `requirements_path` is resolved relative to `code/pyapp/`.
- **Problem:** `requirements_path = "requirements.txt"` names the same file. The export then replaces the developer's input with the fully pinned output, including transitive packages, which the next start reads as direct requirements. The settings comment says "The launcher only reads it".
- **Recommendation:** Refuse the export (with a message) when the two paths are the same file, or export to a different default name such as `requirements.lock.txt`.
- **Verification:** Test with `requirements_path` set to the export path; `cmd_export` must raise `SetupError` before running uv.

### F21 — `clean` reports deleting diagnostics it kept

- **Severity / Confidence / Category:** Low · Confirmed · Bug, messages
- **Location:** `DC/scripts/dev_tools/housekeeping.py:130-137`
- **Current behavior and evidence:**
  ```python
  if ProcessRegistry(paths.PROCESS_REGISTRY_DIR).records()[0]:
      print_warn("Kept the per-run diagnostics: close the running app instance(s) first.")
  else:
      remove_tree_inside(paths.RUNS_DIR, paths.TEMPORARY_DIR)
  runs = " and the per-run diagnostics" if "runs" in keys else ""
  print_success(f"Deleted {deleted} log file(s){runs}.")
  ```
- **Problem:** With an instance running, the warning is followed by "Deleted N log file(s) and the per-run diagnostics."
- **Recommendation:** Set a flag in the `else` branch and build the message from it.
- **Verification:** Extend `test_run_folders_are_kept_while_an_instance_runs` to assert on the output.

### F22 — The shortcut record is lost on partial failure

- **Severity / Confidence / Category:** Low · High confidence · Robustness
- **Location:** `DC/scripts/dev_tools/housekeeping.py:148-149`; `DC/actions/setup.py:118-140`
- **Current behavior:** `remove_shortcuts` writes an empty record even when some shortcuts could not be deleted (a warning is printed per file). Setup writes the record only after every shortcut was created.
- **Problem:** A shortcut that Explorer holds open, or a Desktop write blocked by Controlled Folder Access halfway through Setup, leaves `.lnk` files that no later run knows about.
- **Recommendation:** Keep the paths that failed in the record; in Setup, write the record in a `finally` with what exists so far merged with the previous list.
- **Verification:** Test `cmd_remove_shortcuts` with `Path.unlink` patched to raise for one path.

### F23 — `status` aborts on an unreadable requirements file

- **Severity / Confidence / Category:** Low · High confidence · Robustness
- **Location:** `DC/scripts/dev_tools/housekeeping.py:157-193`, label at `:166`
- **Current behavior:** `validate()` problems are caught and shown as the "Settings" row. Afterwards `all_packages(s)` and `requirements_file_entries(s)` are called outside any `try`.
- **Problem:** A missing or unreadable `requirements_path` file is reported by `validate()` and then raised again as `SettingsError`, which ends the tool. The README names `status.cmd` as the first thing to run when something is wrong. Separately, a uv outside the project is always labeled "(global)", including the launcher's own shared copy, and the prefix test also matches `generated\uv-cache`.
- **Recommendation:** Compute the package rows inside `try/except SettingsError` and show the message in the row. Label the uv as local, shared or global by comparing with `LOCAL_UV_EXE` and `SHARED_UV_EXE`.
- **Verification:** Test `cmd_status` with `requirements_path` pointing to a missing file.

### F24 — Start can misreport a cancelled launch as a failed one

- **Severity / Confidence / Category:** Low · High confidence (very small window) · Race condition
- **Location:** `DC/actions/start_program.py:136-148`; `DC/runtime/bg_watchdog.py:176-178`
- **Current behavior:** Each loop iteration reads `startup.json`, then checks whether the watchdog process has ended.
- **Problem:** When the watchdog's own policy check cancels the launch, it writes `status: "cancelled"` and exits at once. If that happens between the read and the `poll()`, the loop raises "The watchdog exited before startup" although the status is there.
- **Recommendation:** After `poll()` reports an exit, read `startup.json` once more before raising.
- **Verification:** Unit test with a fake child whose `poll()` writes the file as a side effect.

### F25 — `;` in the program name or path is not escaped for `wt.exe`

- **Severity / Confidence / Category:** Low · Needs verification · Bug
- **Location:** `DC/actions/start_program.py:115-122`
- **Current behavior:** In Windows Terminal mode the command is `wt.exe --title <program_name> [--tabColor …] <python> … <paths>`.
- **Problem:** `wt.exe` treats `;` as a separator between its own subcommands. A program name such as `My App; beta` or a project folder containing `;` would split the command line.
- **Recommendation:** Replace `;` with `\;` in every argument passed after `wt.exe`, and add a test for the built argument list.
- **Verification:** Set `use_classic_terminal = False` and `program_name = "A; B"`, start the app.

### F26 — `classic_terminal=False` is never used; docs describe the wrong target

- **Severity / Confidence / Category:** Low · Confirmed · Dead code, documentation
- **Location:** `DC/scripts/shortcuts.py:65, 82-83, 198, 233`; `DC/actions/setup.py:126-135`; `DC/README.md:70-72`; `DC/pyapp_tools/src/get_startup_time.py:84-85`
- **Current behavior:** `generate_shortcut` has a `classic_terminal` parameter. Setup is its only caller and never passes it, so every shortcut targets `conhost.exe "<…>\B\X.bat" "<argument>"`.
- **Problem:** The `cmd.exe /d /c call …` branch cannot run. The launcher README still says the shortcut target is `cmd /d /c call "...\DONT_CHANGE\B\W.bat" <app id>`, and the start-up benchmark measures that form instead of the real one.
- **Recommendation:** Remove the parameter and the branch, correct the README sentence, and start the benchmark through `conhost.exe` like the shortcuts do.
- **Verification:** `git grep classic_terminal` returns nothing; `test_shortcut_file_names` still passes.

### F27 — File tables trail renames; 11 test files are not listed

- **Severity / Confidence / Category:** Low · Confirmed · Documentation
- **Location:** `DC/README.md:325-329, 339-340`; `DC/tests/README.md:16-33`; `DC/tests/support.py:33`; `DC/TODO.md:3, 9-13`
- **Problems:**
  - `DC/README.md` lists `dev/common.py`, `dev/packages.py`, `dev/py_vers.py`, `dev/self_contained.py`, `dev/housekeeping.py`; the folder is `scripts/dev_tools/`.
  - The same file says the import map is "generated by the Dev Helpers' `make_import_map.py`" and lists only five of the tools in `pyapp_tools/`.
  - `DC/README.md:256` and `:342` say the license files cover "the bundled font (see Licensing)", but the Licensing section and `LICENSE.md` do not mention the font.
  - `DC/tests/README.md` describes 16 test files; 27 exist. Missing: `test_app_workflows`, `test_dev_menu`, `test_git`, `test_git_leaks`, `test_output_logs`, `test_release`, `test_resolve_runtime`, `test_staged_ruff`, `test_template_contract`, `test_template_repo`, `test_tools`.
  - `tests/support.py:33` mentions `scripts/environment`; the package is `scripts/env`.
- **Impact:** The launcher README is advertised as documenting every file; a reader following it looks for folders that do not exist.
- **Recommendation:** Fix the names. To stop the drift, add a test like the existing `test_referenced_scripts_exist` that checks every back-quoted relative path in the two tables.
- **Verification:** The new test passes.

### F28 — Annotation breaks `typing.get_type_hints()` on Python 3.8

- **Severity / Confidence / Category:** Low · Confirmed · Typing, convention
- **Location:** `DC/scripts/image_tools.py:6, 74`
- **Current behavior:** `from collections.abc import Iterable` and `icon_sizes: Iterable[int] = (…)`.
- **Problem:** The launcher's own rule (`DC/README.md:50-55`, `ruff.toml` `keep-runtime-typing`) is that annotations stay evaluable on 3.8. `collections.abc.Iterable` is not subscriptable there.
- **Evidence:** On Python 3.8.20: `typing.get_type_hints(image_tools.generate_ico_from_png)` → `TypeError: 'ABCMeta' object is not subscriptable`. `tests/test_annotations.py` passes on 3.8, so its module list does not include `image_tools`.
- **Impact:** None at run time today; it is a hole in a rule the project enforces by test.
- **Recommendation:** `from typing import Iterable`, and build the test's module list by walking the package instead of naming modules.
- **Verification:** `test_runtime_type_hints` covers `image_tools` and passes on 3.8.

### F29 — Every test process leaks a temporary folder

- **Severity / Confidence / Category:** Low · Confirmed · Tests
- **Location:** `DC/tests/project_location.py:19`
- **Current behavior:** Importing the module creates `tempfile.mkdtemp(prefix="pyapp-tests-")` for the diagnostics log and never removes it.
- **Problem:** A parallel run starts one process per test file, so one run leaves about 28 folders. Twelve such folders from earlier runs were found in `DC/tmp/` on the audit machine (runs with `TEMP` pointing there).
- **Recommendation:** Register `atexit.register(shutil.rmtree, folder, ignore_errors=True)`, or use one fixed folder name.
- **Verification:** Count `pyapp-tests-*` folders in `%TEMP%` before and after a run.

### F30 — A blocked uv is reported as an outdated one

- **Severity / Confidence / Category:** Low · High confidence · Messages
- **Location:** `DC/bootstrap/resolve_runtime.py:405-418`
- **Current behavior:** If `uv --version` fails for the global uv, `version` is `None` and the candidate is recorded as `outdated = f"{candidate} ({version})"`.
- **Problem:** The resulting text is "global uv C:\…\uv.exe (None) does not satisfy uv_version ''". The real reason (the program was refused by policy) is stored in `_start_problems` and not shown on this path.
- **Recommendation:** When `version is None`, raise `BootstrapError(_start_problems[-1])` or say "could not be started".
- **Verification:** Unit test with `uv_version_of` patched to return `None`.

### F31 — PATH entry comparison is exact text

- **Severity / Confidence / Category:** Low · High confidence · Robustness
- **Location:** `DC/bootstrap/resolve_runtime.py:352-362`
- **Current behavior:** `add_to_user_path` appends the folder unless `str(folder)` is already one of the `;`-separated entries.
- **Problem:** `%USERPROFILE%\.local\bin`, a different letter case or a trailing backslash is the same folder but not the same text, so a duplicate is added. The value is also always written back as `REG_EXPAND_SZ`.
- **Recommendation:** Compare `os.path.normcase(os.path.normpath(os.path.expandvars(entry)))`, and keep the value's existing registry type.
- **Verification:** Unit test with a fake registry key (the function already takes `key_path`).

### F32 — Probe and cleanup steps can end in a raw traceback

- **Severity / Confidence / Category:** Low · High confidence · Error handling
- **Location:** `DC/bootstrap/resolve_runtime.py:486-496` (`remove_broken_python_links`), `DC/scripts/env/pythons.py:22-30` (`interpreter_version`), `DC/runtime/bg_watchdog.py:189-201`
- **Problems:**
  - `entry.rmdir()` for a dead junction is not guarded; a permission error fails the whole bootstrap over a cosmetic cleanup.
  - `interpreter_version` uses `check_output` with a timeout; `CalledProcessError`, `TimeoutExpired` and `OSError` (a blocked interpreter) reach the user as a traceback instead of the policy explanation the bootstrap has for the same case.
  - In the watchdog, `load_settings()` and `main_script_path()` run before the `try` whose handler tells the waiting launcher what went wrong.
- **Recommendation:** Suppress `OSError` around the `rmdir`; convert the three exceptions in `interpreter_version` to `SetupError` with the executable's path; move the two watchdog calls inside the `try`.
- **Verification:** Unit tests with the subprocess call patched to raise.

### F33 — Leak check skips UTF-16 text and loads the whole history

- **Severity / Confidence / Category:** Low · High confidence · Security tooling
- **Location:** `DC/pyapp_tools/src/check_git_leaks.py:170-171, 196-198`
- **Current behavior:** A file with a NUL byte in its first 8 KB is treated as binary. The history scan reads the complete output of `git log --all -p` into one string.
- **Problem:** UTF-16 text (PowerShell 5.1 redirection, some exports) contains NUL bytes and is never scanned. For an app repository with a long history, the single string can reach gigabytes; `data/workflows/leaks.yml` runs this in CI with `fetch-depth: 0`.
- **Recommendation:** Detect a UTF-16 byte-order mark and decode instead of skipping. Read the log through `subprocess.Popen` line by line; `parse_history` already works on lines.
- **Verification:** Test with a UTF-16 file holding a token in one of the recognized formats.

### F34 — 1,084 lines of working notes ship with the launcher

- **Severity / Confidence / Category:** Low · Confirmed · Repository hygiene
- **Location:** `DC/TODO.md`
- **Current behavior:** The file is tracked inside `DONT_CHANGE`, so it is part of every app made from the template and of every release zip (`release.py` packs all tracked files of the folder).
- **Problem:** Beyond the first sections it is a raw personal log (for example lines 625–626, 809–823, 869–889) with many typos, and it refers to things that are not in the repository ("Dev Helpers `future/TODO.txt`", `make_portable`).
- **Recommendation:** Keep a short, curated list (or GitHub issues) and move the notes out of the shipped folder, or exclude the file from the release zip.
- **Verification:** Not applicable.

### F35 — Copies with the same program name overwrite each other's shortcuts

- **Severity / Confidence / Category:** Low · High confidence · Design
- **Location:** `DC/actions/setup.py:110-112`; `DC/scripts/shortcuts.py:282-295`
- **Current behavior:** The taskbar identity includes a hash of the project folder, so every copy is distinct. The Start Menu folder and the Desktop file names are derived from `program_name` only.
- **Problem:** Two copies that keep the same name (a development copy and a released copy) write the same `Programs\<name>\*.lnk` and Desktop files. The last Setup wins. The README says "two apps made from this template never mix their windows", which holds for windows but not for these shortcuts.
- **Recommendation:** Before overwriting, detect that the existing `.lnk` targets another existing project (the check in `is_generated_shortcut` already reads the target) and warn, or append a short suffix.
- **Verification:** Run Setup in two copies; the Start Menu entry of the first must still start the first, or a warning must appear.

### F36 — "compatibitly"

- **Severity / Confidence / Category:** Low · Confirmed · Spelling
- **Location:** `code/pyapp/developer_settings.py:13`; `DC/data/dev_settings_default.py:13`
- **Current text:** `# For backwards compatibitly down to Python 3.8:`
- **Recommendation:** `# For backward compatibility down to Python 3.8:` in both files (a test requires them to be identical).
- **Verification:** `test_settings.py` (defaults file matches the template) still passes.

### F37 — `str.isdigit()` accepts text `int()` rejects

- **Severity / Confidence / Category:** Optional · Confirmed · Input handling
- **Location:** `DC/runtime/process_exit.py:224`; `DC/scripts/dev_tools/main.py:156`; `DC/scripts/dev_tools/packages.py:73, 167`; `DC/scripts/dev_tools/housekeeping.py:113`
- **Problem:** `"²".isdigit()` is `True` but `int("²")` raises `ValueError`, which ends the menu with a traceback.
- **Recommendation:** Use `answer.isdecimal()` or compare against the set of valid strings, as `venv.handle_version_change` already does (`answer in {str(i) for i in …}`).
- **Verification:** Menu test with `"²"` as input.

### F38 — System programs are started by bare name

- **Severity / Confidence / Category:** Optional · High confidence · Hardening
- **Location:** `DC/scripts/console_tools.py:391, 436`; `DC/runtime/bg_watchdog.py:152`; `DC/actions/start_program.py:117, 124`; `DC/scripts/image_tools.py:26`; `DC/scripts/env/venv.py:510`; `DC/scripts/shortcuts.py:233`
- **Current behavior:** `cmd.exe`, `conhost.exe`, `notepad.exe`, `powershell.exe` and `wt.exe` are started without a path.
- **Problem:** `CreateProcess` searches the current directory before `System32`. The terminal shortcuts keep the shortcut's start folder as the current directory.
- **Impact:** Small: whoever can place a file in the project folder can already change `main.py`. It matters for folders shared with less-trusted users.
- **Recommendation:** Build the paths from `backend_settings.WINDOWS_DIR` (`System32\cmd.exe` and so on); `DC/run.bat:16` already does this for Notepad.
- **Verification:** `test_files.py` could assert that no bare system program name appears in an argument list.

### F39 — A newer uv is fetched for any Python install failure

- **Severity / Confidence / Category:** Optional · High confidence · Efficiency
- **Location:** `DC/bootstrap/resolve_runtime.py:446-457, 570-576`; `DC/scripts/env/pythons.py:102-105`
- **Current behavior:** When `uv python install` fails, the shared uv is installed and the install is retried, whatever the reason.
- **Problem:** Offline or behind a blocking proxy, this adds a second failing download, or copies the same uv version into `%LOCALAPPDATA%\PyApp-Template\uv` and then discards the result because it is not newer.
- **Recommendation:** Retry with a newer uv only when the requested version is absent from `uv python list --only-downloads` (the data `available_summary` already reads).
- **Verification:** Extend `test_uv_fallback.py`.

### F40 — Restoring the console also un-maximizes it; title keeps `\n`

- **Severity / Confidence / Category:** Optional · High confidence · Cosmetic
- **Location:** `DC/scripts/console_tools.py:300-311, 146-157`
- **Problem:** `ShowWindow(hwnd, SW_RESTORE)` is called without checking `IsIconic`, so a window the user maximized is shrunk when an error is shown. `set_terminal_title` removes `\r\n` and `\r` but not a lone `\n`.
- **Recommendation:** Restore only when `IsIconic(hwnd)` (as `windows_focus.focus_window` does); strip all line breaks from the title.
- **Verification:** Manual.

### F41 — Only five crash codes are recognized

- **Severity / Confidence / Category:** Optional · High confidence · Messages
- **Location:** `DC/scripts/runtime_state.py:578-591`
- **Current behavior:** The wording "crashed" versus "ended unexpectedly" depends on a set of five NTSTATUS values.
- **Problem:** Common ones are missing: `0xC0000374` (heap corruption), `0xC0000094` (integer division by zero), `0xC0000135` and `0xC0000142` (DLL not found or failed to initialize), `0xE06D7363` (C++ exception).
- **Recommendation:** Treat every code `>= 0xC0000000` as a crash except `0xC000013A` (Ctrl+C).
- **Verification:** Extend the existing table-driven test.

### F42 — Import finder scans environments not named with a dot

- **Severity / Confidence / Category:** Optional · High confidence · Usability
- **Location:** `DC/scripts/import_finder.py:69-80`; `DC/backend_settings.py:163-169`
- **Problem:** Only folders starting with `.`, `__pycache__` and `node_modules` are skipped. A `venv`, `env`, `build` or `dist` folder inside `code/` is scanned, which lists the imports of every installed package.
- **Recommendation:** Skip any folder that contains `pyvenv.cfg`, and add `build`, `dist` and `site-packages` to the exclusion list.
- **Verification:** Test with a fake `venv/pyvenv.cfg`.

### F43 — No CI on `dev`; actions pinned by tag

- **Severity / Confidence / Category:** Optional · Confirmed · CI
- **Location:** `.github/workflows/pyapp-template-launcher-tests.yml:4-8`, `pyapp-template-fresh-clone.yml:4-8`; all `uses:` lines; `DC/data/workflows/leaks.yml:20`
- **Current behavior:** The test workflows run for pushes and pull requests to `main`. Development happens on `dev`. Actions are referenced as `actions/checkout@v7.0.1` and `astral-sh/setup-uv@v10.3.3` (both versions exist).
- **Problem:** A push to `dev` is checked only by the local pre-push hook. Tags can be moved by the action's owner; a commit SHA cannot.
- **Recommendation:** Add `dev` to the push branches, or rely on pull requests into `main` and say so. Pin to SHAs if supply-chain exposure matters; the copied `leaks.yml` runs in every app repository that enables it.
- **Verification:** A push to `dev` shows a workflow run.

### F44 — Per-write overhead; crash logs copy the whole log

- **Severity / Confidence / Category:** Optional · High confidence that the work is done; the cost needs a benchmark · Performance
- **Location:** `DC/runtime/script_wrapper.py:108-137, 171-176, 197-260`; `DC/runtime/process_exit.py:130-140`
- **Details:** See section G, items 1 to 3.

### F45 — Fixed start-up timeouts

- **Severity / Confidence / Category:** Optional · High confidence · Configuration
- **Location:** `DC/runtime/bg_watchdog.py:316-323` (30 s until the wrapper reports ready); `DC/actions/start_program.py:135` (120 s for the acknowledgement)
- **Problem:** The first start of a fresh environment on a slow disk with real-time scanning can exceed 30 s before the interpreter has loaded the wrapper. The result is "The application wrapper did not become ready" and a terminated app.
- **Recommendation:** Name the two values in `backend_settings.py`, and make the first one generous (for example 120 s); the loop already ends early when the child exits.
- **Verification:** Not applicable.

### F46 — Seven identical wrappers; small redundancies

- **Severity / Confidence / Category:** Optional · Confirmed · Maintainability
- **Location:** `DC/pyapp_tools/{check_git_leaks,fresh_clone_test,get_import_times,get_startup_time,make_import_map,test_all_pythons,verify_launcher}.bat`; `DC/bootstrap/resolve_runtime.py:151-152`; `code/pyapp/icons/How to change icons.cmd:8`; `.gitignore:34-36`
- **Problems:** The seven `.bat` files differ only in the script name. `setting()` is `settings.get(name, default) if name in settings else default`, which is `settings.get(name, default)`. The label `:result` is never used. `*.py[codz]` repeats `*.pyc` and `*.pyo`.
- **Recommendation:** One `_run.bat <script>` that the others call in a single line; simplify the rest.
- **Verification:** `test_files.py` (batch files, referenced scripts) still passes.

---

## F. Spelling, grammar, and documentation corrections

| File / Line | Original | Suggested correction | Reason |
|---|---|---|---|
| `code/pyapp/developer_settings.py:13`, `DC/data/dev_settings_default.py:13` | `# For backwards compatibitly down to Python 3.8:` | `# For backward compatibility down to Python 3.8:` | Typo |
| `DC/bootstrap/resolve_runtime.bat:132, 140, 144, 215` | `copy a folder made with the make_portable dev tool to this PC` | `copy a folder made with the make_self_contained dev tool to this PC` | The tool was renamed |
| `DC/README.md:71` | ``target `cmd /d /c call "...\DONT_CHANGE\B\W.bat" <app id>` (classic console)`` | ``target `conhost.exe "...\DONT_CHANGE\B\W.bat" "<app id>"` `` | Matches `shortcuts.py:198, 233` |
| `DC/README.md:325-329` | `dev/common.py`, `dev/packages.py`, `dev/py_vers.py`, `dev/self_contained.py`, `dev/housekeeping.py` | `dev_tools/common.py`, … | The folder is `scripts/dev_tools/` |
| `DC/README.md:339` | ``generated by the Dev Helpers' `make_import_map.py` `` | ``generated by `pyapp_tools/src/make_import_map.py` `` | "Dev Helpers" no longer exists |
| `DC/README.md:340` | ``… `verify_launcher` (Ruff, Pyrefly), `get_startup_time`, `get_import_times`, `make_import_map`, `get_longest_paths`.`` | Add `check_git_leaks`, `fresh_clone_test`, `test_all_pythons`, `release` and the Git hooks, or link to `pyapp_tools/README.md` | Incomplete list |
| `DC/README.md:256`, `:342` | `… and of the bundled font.` / `Banner font (see [Licensing](#licensing)).` | Add to the Licensing section: "The banner font `data/fonts/pyapp-grid.tlf` was drawn for this project and is covered by the same license." | The section referred to says nothing about the font |
| `DC/tests/README.md:16-33` | Table with 16 files | Add the 11 missing files (see F27) | Outdated |
| `DC/tests/support.py:33` | `that config and scripts/environment read and write` | `that config and scripts/env read and write` | Folder name |
| `DC/TODO.md:3` | ``Done items are removed; Longer-term ideas: Dev Helpers `future/TODO.txt`.`` | `Done items are removed.` | Capitalization; the file referred to is not in the repository |
| `DC/TODO.md:11` | `` `make_portable` `` | `` `make_self_contained` `` | Renamed |
| `DC/scripts/console_tools.py:161` | `"""Best-effort icon update of the current Windows terminal icon"""` | `"""Set the icon of this console window; errors are recorded, not raised."""` | Repeated word, missing period, says what "best-effort" means |
| `DC/scripts/console_tools.py:381` | `"""colors is in format of windows terminal colors"""` | ``"""`colors`: one or two hex digits as for the Windows `color` command (background, then text)."""`` | Unclear; "Windows Terminal" is a different program |
| `DC/scripts/file_tools.py:34` | `"""makes a path absolute if relative with respect to the file (as if the file defined it)"""` | ``"""Return `path` as an absolute path; a relative one is relative to the folder of `file`."""`` | Grammar, capitalization |
| `DC/scripts/config.py:457` | `A setting written as a triple-quoted block stays one, so a pasted requirements list keeps its form.` | Until F06 is fixed: `… stays one; comments and blank lines in it are not kept.` | Says the opposite of what happens |
| `DC/pyapp_tools/src/get_startup_time.py:5` | `The copy is then started the way its shortcuts start it` | `… started through cmd.exe (the shortcuts use conhost.exe)`, or change the command | See F26 |
| `DC/pyapp_tools/README.md` (hooks row), `DC/CHANGELOG.md` | `apps built from the template are left alone` / `(never in an app built from it)` | Describe the real condition: "in any clone whose `origin` is named PyApp-Template at the time Setup runs" | See F03 |
| `.gitignore:1` | `# Entries in this file will not be synchronized in git. ` | `# Git does not track the entries in this file.` | Trailing space; "Git" |
| `.gitignore:6` | `# "!" before a line whitelists synchronization. Must come after rule that stops sync.` | `# "!" before a pattern keeps a file that an earlier rule ignores.` | Clarity |

Not proofread line by line: `DC/CHANGELOG.md` and `DC/TODO.md` beyond the parts named in section C.

---

## G. Performance improvement opportunities

**1. Output path of the app (`script_wrapper.PipeSplitter.write`).** Every `write()` call takes the native-output lock and issues a read on the raw file, formats the time twice with `datetime.now().astimezone().strftime()` at a line start, writes to the console stream and the log, and flushes both. `print("x")` is two `write()` calls. Expected benefit of batching: large for apps that print thousands of lines per second, none for typical GUI apps. Options: flush the console stream only at line ends; format the prefix once when both formats are equal; reuse the formatted text within the same second. Trade-off: slightly later output on the console in exchange for fewer system calls. **A benchmark is needed first**; `get_startup_time.py` has the right structure to host one (a probe that prints N lines with and without logging).

**2. Crash logs duplicate the log (`process_exit.append_printed_output`).** Each crash log gets a complete copy of the run's normal log. For a long-running app with a log of hundreds of megabytes, every crash doubles it. Appending the last N kilobytes and naming the full log's path keeps the "one file tells the story" idea at bounded cost. No benchmark needed; this is about disk space.

**3. Raw output file (`NativeOutput`).** `.output.log` receives everything that bypasses Python's streams and is never truncated during a run; it is removed only after a normal end. Apps whose child processes write a lot keep two growing files. A size cap with rotation would bound it. Low priority.

**4. First start after an environment change (F02).** Fixing the fingerprint removes one full `uv lock --check` plus `uv sync` round on the second start after every Setup or package change. This is the most visible gain and needs no benchmark.

**5. Leak check history scan (F33).** Streaming `git log -p` instead of materializing it keeps memory flat. Relevant for app repositories with a long history, not for the template.

**6. Icon identification (`image_tools.get_png_image_id`).** The decoded pixels travel as base64 JSON through a pipe (about 1.4 MB for 512², about 85 MB for 4096²). Computing the CRC inside the PowerShell script and returning only the result removes that. Negligible for the shipped images.

**7. Start-up path.** `start_program.py` imports the complete environment stack before the fast-path check. `get_import_times.bat launcher` exists to measure this; the audit did not run it. Measure before changing anything.

---

## H. Architecture and maintainability improvements

**High-value**

- **One definition of the uv environment (F14).** Three hand-maintained copies in batch and Python are the root of the drift. The batch stage only needs "a uv and any Python ≥ 3.8", so it can stop setting install-related variables and leave installing the project's Python to `resolve_runtime.py`. That leaves two Python copies, which a test can keep equal.
- **Completion handling without a console (F04, F05).** `process_exit.py` mixes three concerns: deciding the outcome, side effects (sound, crash log, opening files) and interactive prompts. Separating the prompts from the rest makes the windowless case a plain call and removes the hang by construction.
- **A checkable list of outside effects.** The README section "What it changes on your PC" does not mention `core.hooksPath` (F03) or the `%LOCALAPPDATA%\PyApp-Template\uv-bootstrap` folder. One function per outside effect, each named in that section, makes the promise "everything stays in the project folder, with these exceptions" verifiable.
- **Documentation tables checked by tests (F11, F26, F27).** The repository already tests that referenced scripts exist and that the changelog names the version. Extending that to the file tables and to retired names would have caught four findings of this audit.

**Optional refactoring**

- Remove `classic_terminal` (F26) and collapse the seven tool wrappers (F46).
- `config.validate()` is one 120-line function with a local helper. A table of `(name, predicate, message)` would be shorter and let the tests iterate over it. Worth doing only when settings are next added.
- `shortcuts.generate_shortcut` defines its COM structures inside the function on every call. Moving them to module level, next to those in `com_tools.py`, would make the function readable. No functional gain.
- `runtime_state.py` holds five topics (file lock, JSON, registry, jobs, log names). It is cohesive enough today; split it only if it grows.

---

## I. Missing and recommended tests

| Test | Behavior to verify | Related |
|---|---|---|
| Launcher ignores app modules named like stdlib modules | Temporary project with `code/random.py` that raises; `entrypoint.py` with a trivial tool exits 0 | F01 |
| Fingerprint ignores `__pycache__` in `site-packages` | Fingerprint equal before and after creating `site-packages/__pycache__`; different after adding a `*.dist-info` folder | F02 |
| Hooks stay off, or become inactive, for an app | `enable_template_git_hooks` with a remote that is later changed; the hook exits 0 | F03 |
| Windowless completion handler never waits | `process_exit.py` under `CREATE_NO_WINDOW` with a broken settings file ends within a timeout | F04 |
| Report survives a crash-log failure | `crash_log_path` below a file; the output still contains the rendered traceback | F05 |
| Comments in the `packages` block survive edits | Full-line and trailing comments remain after `set_list_setting` | F06 |
| Color string for one unset color | `bg="9", text=None` → `"97"`; equal colors rejected by `validate` | F07 |
| Junction leading outside the base | Link removed, target intact (Windows only) | F08 |
| Diagnostics summary with a chained exception | Count is 1, "last" is the header line | F09 |
| `uv_version = ">=0..9"` | Rejected by `validate` and by the bootstrap with a message | F10 |
| No retired names in messages | `make_portable`, `Dev Helpers`, `dev/` absent from launcher sources and READMEs | F11, F27 |
| uv environment lists are equal | `resolve_runtime.OWN_UV_VARIABLES` against `uv._OWN_UV_VARIABLES` | F14 |
| Registry keeps a record it cannot read | `read_text` raises `PermissionError`; the file remains, no exception | F15 |
| `PROPVARIANT` size | 24 bytes on x64 | F17 |
| Dropped dependency groups are reported | `[dependency-groups]` in `pyproject.toml` → warning | F19 |
| Export refuses the `requirements_path` file | `SetupError` before uv runs | F20 |
| `clean` message while an instance runs | No "and the per-run diagnostics" in the success line | F21 |
| `status` with a missing requirements file | The tool completes and shows the problem in a row | F23 |
| Start loop re-reads the status after the child ended | "cancelled" written between read and poll → return 0 | F24 |
| `wt.exe` argument escaping | `;` becomes `\;` | F25 |
| Annotation test covers every launcher module | Module list built by walking the package | F28 |
| Leak check on UTF-16 text | A token in a UTF-16 file is found | F33 |
| Menus with non-ASCII digits | `"²"` → "Please enter a number", no traceback | F37 |

Areas with no automated coverage today, by the tests' own README ("Manual release check"): Setup end to end, shortcut creation through COM, the instance policies with real windows, `change_python`, `make_self_contained`, a moved and a copied folder. The fresh-clone test covers Setup and one no-terminal start. A second scenario that starts the app twice would cover F02.

Test results of this audit, for reference: executed successfully — the full suite on Python 3.14.9 and on 3.8.20 (261 tests each, all passed). Failed — none. Not executed — `test_all_pythons` (downloads Pythons), the fresh-clone test (runs Setup), the tests in the uncommitted `test_repository_check.py`. Found by inspection only — every finding not marked "Confirmed".

---

## J. Quick wins

| Change | Effort | Finding |
|---|---|---|
| `sys.path.append` in `entrypoint.py`, `bg_watchdog.py`, `process_exit.py` | trivial | F01 |
| Replace `make_portable` in four batch messages | trivial | F11 |
| Fix "compatibitly" in both settings files | trivial | F36 |
| Print the report before writing the crash log; catch `OSError` around the latter | small | F05 |
| Build the `clean` success message from what was deleted | trivial | F21 |
| Fill a missing color half with the default | trivial | F07 |
| `from typing import Iterable` in `image_tools.py` | trivial | F28 |
| Remove the temporary diagnostics folder at exit in `project_location.py` | trivial | F29 |
| Re-read `startup.json` after the watchdog exited | trivial | F24 |
| Delete the uv archive after unpacking in `resolve_runtime.bat` | trivial | F12 |
| `isdecimal()` in five menus | trivial | F37 |
| Padding field in `PROPVARIANT` | trivial | F17 |
| Count diagnostics entries by header line | small | F09 |
| Stricter `uv_version` pattern in `config.py` and `resolve_runtime.py` | small | F10 |
| Correct the README file tables and the tests README | small | F27 |
| Guard the junction cleanup and `interpreter_version` | small | F32 |
| Remove `site-packages` from the fingerprint | small | F02 |
| Skip prompts in the windowless completion handler | small | F04 |

---

## K. Longer-term improvements

- **Git hooks as an explicit maintainer feature (F03).** Needs a decision on the intended workflow for forks and for apps that keep the template as `origin`.
- **Comment-preserving edits of `packages` (F06).** A small line-based editor for the block, with tests for continuation lines and hashes.
- **Completion handler structure (F04, F05)** as described in section H.
- **One source for the uv environment (F14)** and a shared lock for the per-user folders (F13).
- **Migration for loose Python requests (F18)**, after confirming uv's behavior.
- **Bounded logs** (section G, items 2 and 3).
- **Windows ARM64 and x86.** The bootstrap maps both to uv targets, but the README promises x64 only and nothing tests the others. State them as untested, or add a CI job when runners are available.
- **Second fresh-clone scenario in CI:** start twice, then Stop. It would exercise the registry, the job object and the fast path on a clean machine.
- **Curated TODO (F34)**, and a release zip without maintainer-only material if the size or content of shipped apps matters.

---

## L. Recommended action plan

1. **Correctness and security**
   1. F01 (`sys.path.append`). No dependencies.
   2. F04 and F05 together; both are in `process_exit.py` and the watchdog's `handle_exit`.
   3. F02. Do this before adding the "start twice" scenario to the fresh-clone test, which would otherwise fail.
   4. F03. Decide the policy first; the code change is small either way.
   5. F06, or as an interim step correct the docstring and print the diff.
2. **Reliability and compatibility**
   1. F10, F15, F24, F32 (error handling at the edges).
   2. F07, F08, F09, F21 (small confirmed bugs).
   3. F12, F13, F14 (bootstrap). F14 first; it reduces what F13 has to protect.
   4. F17, F20, F22, F23.
   5. Verify F16, F18 and F25, then fix what is confirmed.
3. **Tests**
   1. Add the tests of section I next to each fix above.
   2. F28 and F29 (test infrastructure).
   3. Documentation tests for file tables and retired names; they keep F11 and F27 from returning.
4. **Performance**
   1. Measure first: `get_import_times.bat launcher` and a print-throughput probe.
   2. Bound crash-log copies and the raw output file if the measurements or user reports justify it.
5. **Maintainability and documentation**
   1. Section F corrections, F26, F34, F36, F46.
   2. F35 (warn on shortcut collisions).
6. **Optional**
   1. F37–F45 as time allows. F43 (CI on `dev`) is the cheapest of them and protects all other work.

---

## M. Additional observations and uncertainties

**Changes that appeared during the audit (not part of the audited revision).** `check_repository.py` and its test are in progress. They were read once; two remarks. (1) Its `git()` helper returns an empty string when Git fails, so a failing `git ls-files` yields "No problems found" instead of an error. (2) The modified `pre-push` hook now runs it on every push, which adds to F03 for anyone who has the hooks without wanting them. `tests/test_imports.py` was reformatted with shorter lines; Ruff's formatter keeps that layout because of the trailing commas, so it is not a lint problem.

**Could not be confirmed**

| Observation | What is needed to verify it |
|---|---|
| After Stop with Windows Terminal, the tab may stay open showing "[process exited with code 1]", because `TerminateJobObject(handle, 1)` ends the watchdog with a non-zero code and Windows Terminal's close-on-exit setting may keep such tabs. | Run with `use_classic_terminal = False`, start, Stop, and observe the tab under the default Windows Terminal profile. |
| The console copy in `bg_watchdog.copy_output` writes raw UTF-8 chunks to `sys.stdout.buffer`. A multi-byte character split across two reads would show as replacement characters on the console (the log is unaffected). | Print more than 64 KB of non-ASCII text in one burst and compare console and log. An incremental decoder would rule it out. |
| `environment_for_main_py` with a key that differs from an existing variable only in case (`"Path"`) adds a second entry to the environment block; which one Windows uses is not defined. Keys containing `=` are not rejected. | Unit test on the `env` dict passed to `Popen`; decide whether `validate()` should upper-case or reject such keys. |
| The mutex name `Global\PyAppTemplateRegistry-…` is shared across Windows sessions. A second user running the same folder at the same moment may be denied access to a mutex created by the first. The mutex exists only for milliseconds at a time. | Two user sessions on one PC starting the same shared folder. |
| Icon files are compared by hash. If the WPF PNG encoder produces different bytes on another Windows version, regenerating icons on a second PC rewrites all `.ico` files and the record, which shows up as a Git change. | Run `regenerate icons.cmd` on two Windows versions and compare hashes. |
| The Git hooks fall back to `python3`, `python` or `py` from `PATH`. On Windows, `python3` is often the Microsoft Store alias, which exits with an error; the hook then stops the commit with a leak-check message. | Clone on a PC without the launcher's runtime cache and with only the Store alias present. |
| `uv_version` ranges allow uv versions that predate variables the launcher sets (`UV_SYSTEM_CERTS`, `UV_PYTHON_INSTALL_BIN`, `UV_MANAGED_PYTHON`). An old uv would ignore them without an error. uv 0.13.5 knows all of them. | Find the uv version that introduced each variable and state a minimum in the settings comment. |
| `update_python` with `python_source = "system"` runs `uv python install --upgrade` with downloads disabled and reports a generic uv failure. The dev tools README says system Pythons are updated with their own installers. | Run the tool with that setting. A short message instead of the uv error would be friendlier. |
| `clean` looks only at the folder the configured log path resolves to *now*. With date codes in the folder part, older folders are never offered. | Set `log_path = "..\\..\\logs\\%Y-%m\\log.txt"`, create logs in two months, run `clean`. |
| `open_in_editor` falls back to starting `code.cmd` through a command string when no `Code.exe` is found next to it; a `%NAME%` sequence in the file path would be expanded by `cmd.exe`. | A project path containing `%TEMP%` on a PC with an unusual VS Code layout. |
| `make_import_map` writes its cache checkpoint in place. An interruption during the write leaves invalid JSON, which the next run treats as an empty cache. | Interrupt at a checkpoint. An atomic replace avoids it. |

**Design choices worth a sentence in the documentation**

- A `SystemExit` with a non-zero code in a *worker thread* counts as a failed run (`script_wrapper.thread_hook`). Python itself ignores `SystemExit` in threads whatever the code. The README mentions "errors in worker threads" but not this.
- An exception in a Tkinter callback marks the whole run as failed after the window closes, because the wrapper reads `sys.last_value`. Apps that show their own error dialog through `report_callback_exception` are not affected.
- `clean_python_environment` removes every `PYTHON*`, `UV_*` and `PIP_*` variable and sets `PYTHONNOUSERSITE=1` for the app, and therefore for every process the app starts.
- The default mode of `check_git_leaks.py` (and so the `leaks` GitHub Action) fails only on secrets; personal data is a warning. The hooks fail on both. The root README's one-line description of the action ("look for secrets and personal data") does not say which of the two fails the build.

**Checked and found in order**, so they need no further attention: the icon record matches all eight `.ico` files; the shipped `icon.png` has the placeholder ID the generator expects; `dev_settings_default.py` equals `developer_settings.py`; no tracked file is matched by an ignore rule; no file has mixed line endings; the pinned GitHub Action versions exist; the uv options and variables the launcher relies on exist in uv 0.13.5. ZIP extraction, subprocess calls (none uses a shell), the uv download (HTTPS, SHA-256, fails closed on an empty checksum) and the settings editor (validates the result before writing) showed no vulnerability. No secrets or credentials were found in tracked files during reading; the repository's own leak checker was not run as part of this audit.

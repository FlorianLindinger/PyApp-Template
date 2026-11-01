# 🐍 PyApp-Template

Turn a Python script or Tkinter app into a portable Windows x64 application.
Users launch a shortcut; the template manages a local Python runtime, dependencies,
logs, and crash reports. They do not need Python installed.

Start with the included GUI example in `code/main.py`, then replace it with
your own code. A prepared folder can be copied and used offline.

---

## Features and implementation status

**Implemented** means the behavior exists in the active code. **Partial** means
it has the specific limits described below; it is not a promise that every
application or clean-machine configuration has been tested.

### Application runtime and startup

| Feature | Status and behavior |
| --- | --- |
| Editable application source | Implemented: run `code/main.py` without compiling the application. A minimal Tkinter GUI uses the configured app name and icon. |
| Separate app and launcher environments | Implemented: a small embedded backend manages the full application Python and its separate package directory. |
| Setup without preinstalled Python | Implemented for Windows x64: download and prepare local runtimes and dependencies. First setup needs network access, a writable folder, and the required defaults file. |
| Python version selection | Implemented: choose an available MSI-based release by major, minor or exact patch version, or leave the version empty for the latest matching release. |
| Optional Tkinter installation | Implemented: `install_tkinter` selects Tcl/Tk support. CPython's own tests, legacy Tools and documentation are excluded from managed app installation. |
| Transactional installation | Implemented: prepare and validate replacement runtime/package directories before publishing them; retain or restore the previous environment when replacement fails. |
| Download and installation diagnostics | Implemented: validate Python publisher signatures, record download provenance, hash-lock backend requirements, and retain MSI/failure diagnostics. |
| Startup health checks | Implemented: probe actual runtime imports/version and compare package manifests, requirements fingerprints, metadata and payload presence. |
| Dependency isolation | Implemented: managed launches sanitize Python/package-tool environment settings and use `-E -s`. This is not an operating-system security sandbox. |
| Existing global Python | Implemented: optionally resolve an installed interpreter instead of preparing an application runtime. Its dependencies remain the user's responsibility; the backend is still required. |
| Prepared offline folders and relocation | Partial: a prepared folder can run offline and app paths are resolved locally. Rerun setup after a move; generated package command launchers may retain absolute interpreter paths. |
| Working directory | Implemented: select the application script folder or the shortcut's configured launch folder. |
| Application arguments and metadata | Implemented: `args_for_main_py` supplies application arguments; eight public environment variables expose launch-time metadata. Extra shortcut arguments are intentionally not forwarded. |

### Shortcuts, appearance and icons

| Feature | Status and behavior |
| --- | --- |
| Seven configurable shortcut actions | Implemented: terminal start, hidden start, Stop, user settings, normal logs, crash logs and `main.py`. Shortcut names can be changed or disabled. |
| Short shortcut targets | Implemented: compact `B/*.bat` paths leave more room for long project paths. Windows path/filename limits still apply. |
| Terminal modes | Implemented: classic console, Windows Terminal or no application terminal. Windows Terminal must be installed when selected; no automatic fallback is provided. |
| Initial terminal appearance | Implemented: app title/icon, console foreground/background colors, Windows Terminal tab color and minimized startup. Effects depend on the selected terminal. |
| Taskbar identity | Implemented: shortcuts and launched processes receive app identity/icon information. Non-Latin and long names receive stable compact IDs; shortcut filenames respect Windows component limits. |
| PNG-to-ICO generation | Implemented: manually run `code/backend/icons/regenerate icons.cmd` to generate ten app/action/status ICOs with multiple image sizes. Setup does not regenerate them automatically. |
| Configurable icon overlays | Implemented: per-icon overlay scale/alignment, optional overlay removal, bundled fallbacks and unchanged-placeholder detection. Uses Windows WPF without requiring Pillow. |
| File and folder actions | Implemented: open settings or `main.py` using VS Code when available, otherwise Notepad; open configured log directories in Explorer. |
| Setup and icon-command reporting | Implemented: report success/failure, retain the exit code and keep the outer window open for acknowledgement. |
| Icon-instructions launcher | Implemented: open instructions in Notepad; print a three-second countdown and close on successful launch, or retain an error prompt. |
| Explorer housekeeping | Implemented: mark selected project metadata paths hidden in Explorer. This does not change Git tracking. |
| Obsolete shortcut removal | Not implemented: renaming or disabling an action does not remove its previously generated shortcut. Remove old shortcuts manually. |

### Dependencies and developer tools

**Change application packages through [code/backend/dev_tools](code/backend/dev_tools/README.md).**
The guide describes the recommended workflows and all 13 batch commands. A system
`pip` may target another Python; direct changes can leave installation state stale.

| Feature | Status and behavior |
| --- | --- |
| Declared requirements | Implemented: use `DEFAULT_PYTHON_PACKAGES.txt` for app defaults or `install_local_reqs.bat` for this tool folder's `requirements.txt`. Keep input files in Git, even when empty. |
| pip and optional uv | Implemented: use uv when enabled/available, optionally install it locally, and fall back to pip if the uv operation fails. |
| Add, reset, clear and upgrade packages | Implemented: install reviewed imports/local requirements, reset to defaults or inferred imports, empty the package environment, or upgrade current package names. |
| Package inventories | Implemented: save installed or inferred dependency lists, with or without versions, and save installed packages as the default list. |
| Import inference | Partial: explicit tools infer distributions and request review before installation. The defaults-file inference flag is currently bypassed during first runtime installation. |
| Manual package terminal | Implemented: package-name/list shorthand, explicit pip/uv commands, configured uv preference with pip fallback, help/status/save and dependency validation. Relative command adapters survive folder moves; no Python/module prefix is needed. |
| Runtime-change menu | Implemented: keep/cancel, change runtime with defaults or no packages, re-resolve installed names, preserve exact versions, or review inferred dependencies; optionally save new defaults. Successful changes continue the launch. |
| Requirement-change detection | Implemented: fingerprint local requirements and nested `-r`/`-c` inputs. Remote includes are not supported by the startup fingerprint policy. |
| Runtime/package lock records | Partial: record selections and resolved versions. First runtime installation bypasses the package-lock reader. Configured Python components are enforced; a minor selector accepts any matching patch. |
| Concurrent environment changes | Implemented: serialize installs with an interprocess lock and reject package mutations while verified app instances are running. |

### Logs, errors and process control

| Feature | Status and behavior |
| --- | --- |
| Normal text/input logs | Implemented: optional UTF-8 logs with separate console/log print and input prefixes, including timestamps and Python shutdown output. |
| Raw output capture | Implemented: a companion `.output.log` captures combined stdout/stderr, binary writes and inherited child-process output. Detached or separately redirected child output is outside this capture. |
| Independent run diagnostics | Implemented: unique run/log names and per-run startup, traceback and completion files prevent concurrent runs from overwriting one another. |
| Rich application tracebacks | Implemented for exceptions escaping the main script: source context, syntax-error pointers, exception chaining, interpreter/date details, legacy-encoding handling and plain-text fallback. Locals are hidden. |
| Failure classification | Implemented: distinguish normal return, successful/failing `SystemExit`, exceptions, Ctrl+C, wrapper/watchdog failures and abrupt/native exits. Native faults use fault-handler diagnostics. |
| Worker and GUI callback errors | Partial: uncaught worker errors (Python 3.8+) and errors retained by Tkinter's default callback handler make completion fail, including workers finishing after `main.py` returns. Custom hooks and other event loops need application reporting. |
| Exception notes and groups | Not implemented in serialized app tracebacks: exception notes and nested `ExceptionGroup` details are omitted. |
| Completion actions | Implemented separately for success, failure, crash and Ctrl+C: close/wait, open log or source, play a WAV, and change terminal title/colors/status icon where supported. |
| Hidden success and visible failures | Implemented: successful hidden runs can stay hidden; failure handling can open a diagnostic console. |
| Missing-package recovery | Implemented: install a missing distribution, review inferred imports, or use a manual package terminal, then restart after successful recovery. Global-Python mode instead gives manual instructions. |
| Existing-instance policy | Implemented: allow multiple runs, prevent a second run, replace existing runs, or ask before replacement using the configured flags. |
| Stop action and PID protection | Implemented: verify process identity before forced tree termination. Registry changes use a Windows mutex; final cleanup removes empty PID artifacts. Cooperative shutdown is not implemented. |
| Automatic log retention limits | Not implemented: retained logs, run directories and installation diagnostics are not pruned automatically. |
| Source-focused Git and licensing | Implemented: ignore generated runtimes/packages/state, provide a project-license placeholder and retain the template backend's `MIT OR Apache-2.0` licensing. Third-party licenses still apply. |

---

## Quick Start

1. Clone/download/copy this repository
2. Try the Tkinter GUI example in `code/main.py`, or replace it with your application
3. (Optional: Change program settings like Python version or program name under `code/backend/developer_settings.py`)
4. (Optional: Add user settings under `code/settings.py`. Import them in `main.py` via `import settings`)
5. Execute `Setup - run first and after moving folder.cmd` to validate/setup the environments and generate shortcuts
6. Run a generated application shortcut. Declare dependencies in `code/backend/dev_tools/DEFAULT_PYTHON_PACKAGES.txt`; keep this required input in Git, even when it contains no packages. Import inference is an optional, reviewed developer action.

`Setup - run first and after moving folder.cmd` resolves the repository from its
own location. After moving the folder, rerun setup to refresh generated shortcuts.

## Changing dependencies

Close running app instances. Edit
`code/backend/dev_tools/DEFAULT_PYTHON_PACKAGES.txt`, then run
`code/backend/dev_tools/reset_packages_default.bat` to apply the declared set.
Test the app and commit the requirements file. A reset removes packages outside
that set. Set the defaults file's
`auto_find_required_packages_here_and_reset_installed_packages_to_them` flag to
`False` when maintaining an explicit dependency list.

For experiments, use `open_package_terminal.bat`, enter `requests rich`,
`pip install requests` or `uv pip install requests`, then type `exit` so the tool
validates and records the installed state. Bare package names and unprefixed
package actions prefer uv when enabled, with pip fallback. Enter `save` to record
installed versions as defaults, or run
`set_default_packages_versions.bat` or `set_default_packages_names.bat` if those
installed packages should become the declared defaults. Review that file before
committing. See the [package-tool guide](code/backend/dev_tools/README.md).

---

## Project Structure

```text
.
├── code/
│   ├── main.py                        <<< MAIN APP CODE: EDIT THIS
│   ├── settings.py                    <<< END-USER SETTINGS: EDIT AS NEEDED
│   └── backend/
│       ├── developer_settings.py      <<< APP / PYTHON SETTINGS
│       ├── dev_tools/                 <<< DEVELOPMENT TOOLS
│       ├── icons/                     <<< ICON SOURCE & GENERATION TOOLS
│       ├── DONT_CHANGE/               Template internals (see its README)
│       └── ...                        Self explanatory folders   
├── logs/                              Generated program logs
├── crash logs/                        Generated crash reports
```

Edit `code/main.py`, `code/settings.py`, and `code/backend/developer_settings.py`
for normal project work. The `python`, `packages`, `backend_python`,
`backend_packages`, `logs`, and `crash logs` folders are generated locally and
are intentionally excluded from normal Git tracking.

`code/backend/DONT_CHANGE` contains the portable launcher implementation. Its
[own README](code/backend/DONT_CHANGE/README.md) explains the installation
flow, backend settings, safety checks, package lists, diagnostics, and licensing
in detail.

---

## Notes

Tested to work in current Windows 11 Home and Python 3.14. This repository was originally built by Florian Lindinger and can be accessed under https://github.com/FlorianLindinger/PyApp-Template

---

## Licensing

The template-owned backend files in `code/backend/DONT_CHANGE` are available under your choice of the MIT License or Apache License 2.0 (`MIT OR Apache-2.0`). Python distributions and third-party packages retain their own licenses and are excluded from normal Git tracking.

Projects created from this template must replace the project-license placeholder in [`LICENSE.md`](LICENSE.md) with their chosen license. See that file for the complete scope and third-party exceptions.

## Arguments, isolation, and dependency updates

`args_for_main_py` in `developer_settings.py` configures the arguments passed to
`main.py`. Generated shortcuts do not forward additional command-line
arguments to the application. Launcher state such as terminal mode is never added
to `main.py`'s positional arguments.

The launcher exports these environment variables for `main.py` to read through
`os.environ`:

| Variable | Value |
| --- | --- |
| `PROGRAM_NAME` | Configured application name |
| `ICON_PATH` | Absolute application icon path |
| `PROGRAM_HAS_TERMINAL` | `"1"` for terminal launches, otherwise `"0"` |
| `LOG_PATH` | Resolved text-log path for this run, or `""` when logging is disabled |
| `APP_ID` | Taskbar identity supplied by the launcher, or `""` when absent |
| `WDIR_IS_SCRIPT_DIR` | `"1"` when the script directory is selected as the working directory, otherwise `"0"` |
| `CLOSE_AFTER_FAILURE` | Configured failure-close policy as `"1"` or `"0"` |
| `CLOSE_AFTER_SUCCESS` | Configured success-close policy as `"1"` or `"0"` |

These are launch-time snapshots. Changing them in `main.py` does not change the
watchdog's settings. For booleans, compare with `"1"`; `bool("0")` is also true.
`PROGRAM_HAS_TERMINAL` describes the launch mode; logging can still make stdout
a pipe rather than a terminal.

Generated shortcuts set Start in to the repository root. Set a shortcut's Start in directory explicitly
when using `start_in_shortcut_folder=True`. Relative-to-launch log paths use
the same captured directory even after backend setup changes its working directory.

The supported managed platform is **Windows x64 (AMD64)**. Native ARM64 and
32-bit runtime installation are not implemented. The installer rejects those
architectures before downloading/replacing a runtime. Python 3.5+ compatibility
is retained in the frontend wrapper, but the regression suite currently covers
the locally available Python 3.12, 3.13, and 3.14 interpreters.

Managed and global launches use `-E -s`: `PYTHONHOME`, `PYTHONPATH`, and user-site
packages do not affect them. Global mode resolves one actual interpreter and
does not automatically modify it. Missing-package errors show its path and a
manual command; the local environment is not modified as a substitute.

The template records exact runtime selection in `code/backend/frontend-python.lock.json`
and resolved default packages in `DEFAULT_PYTHON_PACKAGES.txt.lock.json` beside
the requirements file. Both are generated local files ignored by the current
`.gitignore`; the requirements inputs themselves should be tracked. Changing
requirements (including local `-r`/`-c` includes) invalidates a package lock.
Deliberately remove a lock to request fresh resolution. Reuse is currently
incomplete: first runtime installation bypasses the package-lock reader.
`python_version = "3.14"` requires 3.14 and accepts any 3.14.x patch;
`"3.14.6"` requires that exact patch. Keeping an incompatible installation cancels
the launch instead of running it. A runtime lock selects a compatible exact
download when rebuilding; it does not tighten a configured minor selector.
These locks are not currently a
complete reproducible-release guarantee. Preserve a prepared folder for an
offline distribution.

## How installation health is checked

The launcher validates the actual managed Python executable by running it with
`-E -s` and importing `ssl`, `sqlite3`, `ctypes`, `encodings` and `pip`, plus
`tkinter` when requested. A successful probe returns its real version, which
must match the configured version components. File/folder existence alone is
insufficient. The launcher backend separately verifies its exact Python version,
required imports and pinned dependency versions.

Application package installation runs `pip check` before publishing the new
environment. It records a manifest containing the Python version, a fingerprint
of the default requirements and local includes, and hashes of distribution
`METADATA` and `RECORD` files. Startup compares that manifest with the current
inputs and metadata, and checks that in-directory files listed by `RECORD` exist
(excluding generated `.pyc` files). A mismatch triggers repair rather than trusting
an old success marker.

These checks detect many incomplete or stale installations; they do not import
every application dependency, verify every package payload's contents, or prove
that the application works. Dependency consistency is checked during installation
and after closing the managed package terminal, rather than by running `pip check`
on every startup. Run the app's own checks after changing dependencies.

## Logs and diagnostics

Each run has its own directory under `code/backend/DONT_CHANGE/temporary/runs/`.
Logs receive a unique run suffix. The normal UTF-8 log records Python text/input
and atexit callbacks; its `.output.log` companion captures raw combined stdout
and stderr, including binary writes and inherited child-process output. With
logging enabled stdout/stderr are pipes, so applications that require a real
terminal should disable logging for their terminal launch. Detached subprocesses
that redirect their own output are outside this capture.

Set `enable_log_for_Windows_terminal_start = False` for applications that need
console handles or interactive terminal features. To diagnose redirection, check
`PROGRAM_HAS_TERMINAL == "1"` together with `not sys.stdout.isatty()` (and stderr).
This detects redirected output, not proof that the application is incompatible;
an application can warn when a feature it needs requires a TTY. Reporting
`isatty() = True` alone does not restore a console handle. Capturing output through
a Windows pseudoconsole is not implemented.

Uncaught worker and default Tkinter callback errors retain normal stderr output
and make final completion fail. The GUI is allowed to keep running; the launcher
shows its completion error after it closes. A main-script exception takes
precedence if both contexts fail. Applications replacing these exception hooks
or using other event loops own their reporting policy.

Successful runs do not create crash reports. Hidden successful runs remain hidden
when `close_after_success=True`. Failures preserve their diagnostics. Persistent
MSI logs are under `temporary/installation-logs/`; failed backend staging folders
are retained with their diagnostic files. These folders can grow and are not
currently pruned automatically.

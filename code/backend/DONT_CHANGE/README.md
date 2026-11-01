# PyApp-Template backend internals

This folder supplies the portable Windows x64 launcher, isolated app environment,
logging, process tracking and completion handling around `code/main.py`.
Application authors normally edit main.py, settings.py and backend/developer_settings.py.

## Runtime structure

```text
DONT_CHANGE/
  B/               Short targets for generated app shortcuts (W/N/Q/S/M/L/C)
  scripts/
    actions/       App shortcut actions and icon generation
    runtime/       Watchdog, application wrapper and completion handling
    setup/         Shared bootstrap/runner, installers, checks and shortcut generation
    dev_tools/     Package tool implementations
    *_tools.py     Focused reusable helpers
  settings/        Backend requirements, version and runtime paths
```

Public package-tool batches live in `../dev_tools/` beside their default package
list. Root setup and the icon-folder command launcher call the shared runner
directly, without extra forwarding batches.

Batch launchers contain dispatch/bootstrap logic; Python files own the behavior.
App shortcuts deliberately use short targets: `B/W.bat` (terminal), `B/N.bat`
(hidden), `B/Q.bat` (Stop), `B/S.bat` (settings), `B/M.bat` (source), `B/L.bat`
(logs), and `B/C.bat` (crash logs). Keep these names short to reduce the command
length stored in Windows shortcuts. Longer implementation paths stay inside the
batch files. Root setup regenerates shortcuts for these targets.

## Startup and installation

1. Root setup or a generated shortcut invokes a batch target.
2. `scripts/setup/ensure_backend_python.bat` delegates to its PowerShell
   companion. It locks bootstrap, validates actual backend imports and exact
   versions, and adopts a healthy existing installation.
3. When installation is needed, a new embedded runtime and dependency target are
   prepared in staging. Signature/hash checks and module health checks finish
   before replacement. Failed staging diagnostics are retained.
4. App startup validates/prepares its full Python and package environment, creates
   a per-run directory, starts the watchdog, and waits for that run's acknowledgement.
5. The frontend wrapper receives private JSON configuration, initializes logging,
   and executes main.py with only application arguments.

`settings/backend_settings.ini` defines the pinned backend version and approved
installation/finalization locations. The PowerShell bootstrap validates these fixed locations.
The generic embedded downloader refuses an existing destination and uses literal
PowerShell paths. Managed installation supports AMD64; ARM64/x86 fail explicitly.

The embedded backend and full frontend have different purposes. Application
packages are separate from backend packages. Normal managed starts use `-E -s`
and sanitized Python/package-tool environment settings; this is dependency
isolation with ordinary user permissions, not an operating-system sandbox.

## Generated state and recovery

`backend_python/`, `backend_packages/`, `temporary/`, `backend/python/` and
`backend/packages/` are generated and excluded from normal Git tracking.

Runtime and package replacements are staged and verified before directory swaps.
Version/package migration retains the previous runtime until package validation
succeeds. A locked `.previous` backup is reported and not overwritten.

Package state records actual Python, requirements fingerprints, metadata/RECORD
hashes and payload existence. Legacy empty markers migrate through additive
staging to preserve manually installed packages. Explicit reset tools rebuild
from declared defaults. Frontend runtime/default-package locks are generated local
state ignored by the current Git rules. Their reuse is incomplete: first runtime
installation bypasses the package-lock reader. Configured version components are
required: "3.14" accepts any 3.14.x; "3.14.6" requires that exact patch. The runtime
lock chooses a compatible exact download without tightening a minor selector.
Keep requirements inputs
tracked; do not treat current locks as a complete reproducible-release guarantee.

`settings/backend_settings.py` comments identify paths tied to root or nested
`.gitignore` rules. If relocating generated directories, update the corresponding
rules for live folders, staging folders and retained backups. Files inside an entirely ignored runtime/temporary directory inherit
that rule. Source scripts, icon assets and requirements inputs remain tracked.
Backend runtime locations also have fixed batch/PowerShell bootstrap consumers;
changing a Python constant alone does not relocate the whole bootstrap.

Each run owns its startup/status/traceback files and unique logs under
`temporary/runs/`. The `.output.log` companion captures combined native, binary
and inherited child output; the normal UTF-8 log captures Python text/input and
atexit callbacks. Logging uses pipes; disable terminal logging for apps needing
a real TTY. Retained run and MSI diagnostics are not automatically pruned.

The manual package console in `scripts/dev_tools/open_package_terminal.py` parses
Windows arguments without a shell. It accepts bare packages/lists, explicit pip
and uv package commands, and automatic uv preference with pip fallback. Relative
pip/uv adapters and the recovery batch use that same entry point. The console
owns the environment lock, running-instance checks and final package validation;
recovery must not hold the same lock in its parent while waiting for this child.
Healthy startup refreshes the adapters after folder moves and runtime installs.
Uncaught worker errors (Python 3.8+) and errors retained by Tkinter's default
callback handler make final completion fail without closing the GUI immediately.
The watchdog also collects worker failures during interpreter shutdown. Custom
exception hooks and other event loops need their own reporting policy.

## Ownership of shared code

Implementation modules are console_tools, filesystem_tools, process_tools,
python_runtime, package_tools, image_tools, git_tools and shell_tools.
`frontend_environment` owns runtime/package repair, `launcher_ui` owns appearance
and log-path policy, and runtime_state/environment_state own cross-process state
and directory transactions.

Ordinary tools share `entrypoint.run_file` and the batch
`scripts/setup/run_backend_script.bat`: import/main failures are reported once,
nonzero status is preserved, and KeyboardInterrupt becomes 130. Lifecycle workers retain their separate
application completion protocol. Helpers never terminate an existing caller shell.

## Stop and icons

Stop validates process image and creation time, then directly terminates the
verified launcher tree. Old bare PID files never authorize termination.
Registry changes use a Windows mutex; the last instance removes its empty PID
directory and legacy PID/lock artifacts. Stale records left by a killed watchdog
are cleaned during the next launch or Stop.

Icon sources and instructions remain in icon_related; invoke the corresponding
`../icons/regenerate icons.cmd` to regenerate ICO files.

## Maintenance and licensing

The template backend is dual licensed MIT OR Apache-2.0. Python distributions and
third-party packages retain their own licenses. Keep their license/metadata files
when distributing a prepared environment.

Keep app-specific edits outside DONT_CHANGE where possible. Use the documented root launchers.

# PyApp-Template backend internals

This folder supplies the portable Windows x64 launcher, isolated app environment,
logging, process tracking and completion handling around `code/main.py`.
Application authors normally edit main.py, settings.py and backend/developer_settings.py.

## Runtime structure

- `settings/`: backend version/dependencies, paths and verification settings.
- `B/`: short batch targets for generated shortcuts; shared bootstrap/tool runners
  live in `B/helper_scripts/`.
- `scripts/shortcut_targets/`: app launcher, watchdog, frontend wrapper and exit handler.
- `scripts/setup/`: backend finalization, health checks and shortcut generation.
- `scripts/dev_tools/`: package, Git and verification utilities for application authors.
- `scripts/icon/` and `icon_related/`: icon generation and source assets.
- `LICENSES/` and `LICENSE.md`: template backend licensing.

## Startup and installation

1. Root Setup.cmd/Start.cmd or a generated shortcut invokes a batch target.
2. `B/helper_scripts/ensure_backend_python.bat` delegates to its PowerShell
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
installation/finalization locations. The wrapper validates these fixed locations.
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
from declared defaults. Commit the frontend runtime and default-package locks
with a release; they record versions, not a guarantee of identical source builds.

Each run owns its startup/status/traceback files and unique logs under
`temporary/runs/`. The `.output.log` companion captures combined native, binary
and inherited child output; the normal UTF-8 log captures Python text/input and
atexit callbacks. Logging uses pipes; disable terminal logging for apps needing
a real TTY. Retained run and MSI diagnostics are not automatically pruned.

## Ownership of shared code

`generic_helpers.py` and `common_code.py` are compatibility import facades.
Implementation modules are console_tools, filesystem_tools, process_tools,
python_runtime, package_tools, image_tools, git_tools and shell_tools.
`frontend_environment` owns runtime/package repair, `launcher_ui` owns appearance
and log-path policy, and runtime_state/environment_state own cross-process state
and directory transactions.

Ordinary tools share `entrypoint.run_file` and the batch
`B/helper_scripts/run_backend_script.bat`: import/main failures are reported once,
nonzero status is preserved, and KeyboardInterrupt becomes 130. Existing verifier
rescan loops retain their interaction. Lifecycle workers retain their separate
application completion protocol. Helpers never terminate an existing caller shell.

## Stop and icons

Stop validates process image and creation time, then directly terminates the
verified launcher tree. Old bare PID files never authorize termination.
Registry changes use a Windows mutex; the last instance removes its empty PID
directory and legacy PID/lock artifacts. Stale records left by a killed watchdog
are cleaned during the next launch or Stop.

Icon sources and instructions remain in icon_related; invoke the corresponding
batch launchers in B/miscellaneous to regenerate editable PNGs or ICO files.

## Maintenance and licensing

The template backend is dual licensed MIT OR Apache-2.0. Python distributions and
third-party packages retain their own licenses. Keep their license/metadata files
when distributing a prepared environment.

Keep app-specific edits outside DONT_CHANGE where possible. Use the documented root launchers.

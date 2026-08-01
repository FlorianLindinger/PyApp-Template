# PyApp-Template backend internals

This folder is the portable Windows launcher layer of PyApp-Template. It
creates and starts the local Python environments, generated shortcuts, logging,
terminal behavior, process monitoring, and error handling around the
application in `code/main.py`.

Most application work belongs outside this folder:

- `code/main.py` — application code
- `code/settings.py` — application settings
- `code/backend/developer_settings.py` — launcher and development settings
- `code/backend/icons/` — icon source files
- `code/backend/dev_tools/` — user-facing development-tool output

Treat `DONT_CHANGE` as backend implementation code. Changes here are possible,
but make future template updates harder to merge.

## Project structure

```text
DONT_CHANGE/
├── B/                         Short batch launchers
│   ├── backend_tools/          Backend diagnostics and verification launchers
│   ├── dev_tools/              Development-tool launchers
│   ├── helper_scripts/         Shared batch helpers
│   │   └── generic_helpers/    Parameterized reusable batch helpers
│   └── miscellaneous/          Utility launchers, including icon generation
├── backend_tools/              Stand-in/test assets and direct batch runners
├── icon_related/               Icon source assets and instructions
├── scripts/
│   ├── backend_tools/          Python implementations of backend tools
│   │   └── helper_scripts/     Internal helper scripts for backend tools
│   ├── dev_tools/              Python implementations of development tools
│   ├── icon/                   Icon-generation Python scripts
│   ├── setup/                  Backend installation and shortcut generation
│   └── shortcut_targets/       Python targets launched by app shortcuts
├── settings/                   Shared backend settings and dependency lists
├── temporary/                  Generated runtime state
├── backend_python/             Generated embedded Python runtime
├── backend_packages/           Generated backend-only dependencies
└── future/                     Unfinished experiments and deferred ideas
```

### Why the folder is named `B`

`B` means **batch**. It holds the small `.bat` files that start backend
scripts. Generated Windows shortcuts target these batches rather than Python
files directly.

- `B/dev_tools/` starts `scripts/dev_tools/`.
- `backend_tools/` contains direct diagnostic and verification runners. They
  ensure the embedded backend Python when required, then start
  `scripts/backend_tools/`.
- `B/miscellaneous/` contains utility launchers such as
  `generate_icon_pngs.bat`.

The short name keeps shortcut target paths short and predictable on Windows.

## How startup works

1. A generated Windows shortcut starts a batch launcher in `B/`.
2. The launcher ensures the embedded **backend Python** is available.
3. Backend scripts configure the terminal, logging, process monitoring, and
   the full local **frontend Python** environment.
4. Frontend Python runs `code/main.py`.

The two Python environments have different jobs:

| Environment | Purpose |
| --- | --- |
| Backend Python | Small embedded runtime for launcher and support scripts |
| Frontend Python | Full local Python installation that runs the application |

This separation keeps launcher dependencies isolated from application packages
and does not require users to install Python globally.

## Settings and installation

`settings/backend_settings.py` is the shared source of backend paths and
constants. Its relative paths are resolved from the `settings/` folder.

`B/helper_scripts/ensure_backend_python.bat` validates the backend
configuration, calls the reusable
`B/helper_scripts/generic_helpers/install_embedded_python.bat` installer,
and runs backend finalization. The generic installer accepts only the Python
version and installation directory. The backend wrapper uses
`settings/backend_settings.ini` for:

- `backend_python_version` — embeddable CPython version to download
- `backend_python_install_dir_relative_path` — required runtime location
- `backend_python_finish_installation_relative_path` — required finalization
  script

The installer validates these paths against the expected backend locations
before it deletes or executes anything.

To change backend dependencies, edit:

- `settings/backend_packages_list.txt` for runtime dependencies
- `settings/backend_build_tools_list.txt` for temporary installation tools

Reinstall the backend runtime after changing either list.

## What is generated

Do not normally edit these folders:

| Folder | Why |
| --- | --- |
| `backend_python/` | Recreated by the embedded-Python installer |
| `backend_packages/` | Recreated when backend dependencies are installed |
| `temporary/` | Runtime signals, logs, and disposable working files |

These folders are intentionally excluded from normal Git tracking.

## Backend tools

Backend tools are diagnostics and tests; they are not part of normal
application startup.

### Verification

`scripts/backend_tools/verify_backend.py` runs:

1. Ruff lint checking
2. Ruff formatting verification
3. Pyrefly type checking

Run one of these launchers from the `code/` folder:

```bat
backend\DONT_CHANGE\backend_tools\verify_backend_basic.bat
backend\DONT_CHANGE\backend_tools\verify_backend_default.bat
backend\DONT_CHANGE\backend_tools\verify_backend_strict.bat
```

Each launcher ensures the embedded backend Python before running the selected
preset. Configure verification targets and exclusions in
`settings/backend_settings.py`:

- `BACKEND_VERIFICATION_TARGETS`
- `BACKEND_VERIFICATION_EXCLUDED_FILES`
- `BACKEND_VERIFICATION_EXCLUDED_FOLDERS`

Use forward slashes in those configured paths. Exit code `0` means success,
`1` means a check failed, and `2` means a required tool was unavailable.

For launcher testing, set `use_standin_main_script = True` in
`settings/backend_settings.py`. Normal shortcut starts will then run
`backend_tools/standin_main_py_for_backend_tools.py` instead of
`code/main.py`. It is `False` by default; startup-time measurements always
use their dedicated dummy script instead.

Direct batch runners with the same tool names are available in
`backend_tools/`. They ensure the backend Python where needed, then invoke
their Python implementation directly.

### Other tools

- `backend_tools/measure_startup_times.bat` measures startup performance.
- `backend_tools/measure_package_import_times.bat` measures package import
  performance.
- `backend_tools/measure_file_import_times.bat` measures selected module
  import times.
- `backend_tools/test_script_wrapper.bat` exercises frontend-wrapper
  traceback and exit handling.

## Icons

`icon_related/` contains the icon assets and instructions.
`scripts/icon/` contains the Python generators:

- `generate_PNGs_to_be_replaced.py` creates editable placeholder PNGs.
- `generate_icons.py` creates the multi-resolution `.ico` files.

Use the corresponding launchers in `B/miscellaneous/`. See
`icon_related/HOW_TO_CHANGE_ICONS.txt` for the icon-editing workflow.

## Maintenance and licensing

Keep `LICENSE.md` and the license/metadata files in generated Python and
package folders when distributing the template. If bundled dependencies change,
update both the package lists and license information.

When updating from PyApp-Template, keep local changes outside `DONT_CHANGE/`
where possible, record unavoidable backend changes, and rerun backend
verification afterwards.

`future/` contains unfinished experiments and is excluded from backend
verification by default.

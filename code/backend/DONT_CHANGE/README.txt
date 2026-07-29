PyApp-Template backend internals
================================

This folder contains the backend code copied from PyApp-Template:
https://github.com/FlorianLindinger/PyApp-Template

It is named DONT_CHANGE because normal app customization should happen in
the files outside this folder, especially:

- code/main.py
- code/settings.py
- code/developer_settings.py
- code/icons
- code/dev_tools

The backend code here is responsible for shortcut startup, local Python
handling, package installation helpers, logging, terminal behavior, and error
handling around the user-facing Python app.


Backend and frontend terminology
================================

In this project, "backend" means the launcher and support code that makes the
app portable and easy to start.

Inside this folder, "backend Python" means the small embedded Python runtime
used to run the launcher/support scripts. "Frontend Python" means the full local Python installation that runs code/main.py.


How the backend works
=====================

The backend is a small Windows-oriented bootstrap layer around the application.
Its normal flow is:

1. A shortcut starts one of the short batch files in B.
2. The launcher starts backend_python, the embedded Python runtime.
3. Backend scripts prepare logging, terminal handling, process monitoring, and
   the frontend Python environment.
4. Frontend Python runs code\main.py, which is the application entry point.

The embedded runtime keeps launcher dependencies separate from the application
environment. This makes the launcher portable and avoids requiring a system
Python installation for normal startup.


Installation and shared settings
================================

The backend runtime is installed by scripts\setup\install_backend_python.bat.
It downloads the configured Python embeddable ZIP, extracts it into
backend_python, and then runs the finalization script to install backend-only
packages.

The installer and Python scripts share these values from
settings\backend_settings.ini:

- backend_python_version: the exact embeddable CPython version to download.
- backend_python_install_dir_name: the fixed runtime directory name. It must
  remain backend_python; arbitrary paths are intentionally not accepted.
- backend_python_finish_installation_relative_path: the finalization script,
  relative to the settings file. It must remain
  scripts\setup\finish_backend_installation.py.

The installer validates the directory name and compares the fully resolved
target with its fixed expected location before it removes anything. It never
accepts an arbitrary deletion path from the INI file. If you need to upgrade
Python, update the version and then review the generated python3xx._pth and ZIP
names derived by settings\backend_settings.py.

settings\backend_settings.py is the shared source of Python path constants.
Every relative path in that module is resolved relative to the settings folder.
It exposes the backend runtime, backend package lists, frontend paths, launcher
paths, icons, temporary files, and developer-tool locations to the rest of the
backend. scripts\common_code.py contains shared behavior; it imports these
constants rather than defining its own paths.


What is generated and what to edit
==================================

Do not normally edit generated installation folders:

- backend_python is recreated by the backend-Python installer.
- backend_packages is recreated when backend dependencies are installed.
- temporary contains runtime state, logs, signals, and other disposable files.

For normal application changes, edit files outside DONT_CHANGE: code\main.py,
code\settings.py, code\developer_settings.py, code\icons, and code\dev_tools.
developer_settings.py is the intended place for local development preferences,
including whether package installation should try uv before falling back to pip.

To change backend dependencies, edit settings\backend_packages_list.txt. To
change temporary build dependencies used only during installation, edit
settings\backend_build_tools_list.txt. Reinstall the backend runtime afterwards
so backend_packages is rebuilt consistently. Keep license information current
when adding or redistributing a package.


Folder contents
===============

- B
  Short batch files used as shortcut targets. The short names help avoid
  Windows shortcut target length limits and keep startup paths predictable.

- future\ascii_fonts
  ASCII-art font data used by backend terminal output.

- backend_packages
  Third-party Python packages used only by the backend launcher/tooling code.
  The expected package list is documented in settings\backend_packages_list.txt.

- backend_python
  Embedded Python distribution used by backend scripts. It is modified during
  backend setup; see scripts/setup/finish_backend_installation.py and
  backend_python/LICENSE.txt.

- backend_tools
  Local helper scripts for measuring startup/import times and testing backend
  launch behavior.

- future
  Notes, experiments, and deferred ideas for future PyApp-Template work.

- icon_related
  Backend icon resources and icon-generation support files.

- scripts
  Main backend Python scripts. Important entry points include start_program.py,
  background_watchdog.py, open_settings.py, open_log_folder.py, and
  stop_program.py.

- settings
  Shared backend configuration: backend_settings.ini, backend_settings.py, and
  the backend dependency lists.

- temporary
  Temporary backend working folder. Generated files here should not be treated
  as project source.


Important files
===============

- LICENSE.md
  Composite license for this folder, the embedded backend Python runtime, and
  bundled backend packages.

- settings\backend_packages_list.txt
  Source list for backend-only Python packages.

- settings\backend_build_tools_list.txt
  Source list for temporary backend Python build/install tools. These are used
  during backend package installation and removed before finalizing backend
  Python.

- PyApp-Template_TODO.txt
  Development notes for the template itself.

- PyApp-Template_VERSION_x.y.txt
  Version marker for the copied backend template.

- .gitignore and .gitattributes
  Git rules for keeping generated or redistributability-sensitive files under
  control.


Distribution notes
==================

If you distribute this folder, keep LICENSE.md and the license/metadata files
inside backend_python and backend_packages. If you change bundled packages,
update both settings\backend_packages_list.txt and LICENSE.md.

If you only build an app from the template, prefer changing the files outside
DONT_CHANGE instead of editing these internals. That keeps future template
updates easier to apply.

When updating from PyApp-Template, treat DONT_CHANGE as a cohesive unit. Keep
local customizations outside it whenever possible, record unavoidable changes,
and rerun the backend verification tools after merging an update.


Backend tools
=============

backend_tools contains diagnostics and test utilities for the template backend.
They are development tools and are not part of normal application startup.

Backend verification
--------------------

backend_tools\helper_scripts\verify_backend.py runs three read-only checks:

1. Ruff lint checking
2. Ruff formatting verification
3. Pyrefly type checking

From the code folder, run:

    py -3 backend\DONT_CHANGE\backend_tools\helper_scripts\verify_backend.py basic
    py -3 backend\DONT_CHANGE\backend_tools\helper_scripts\verify_backend.py default
    py -3 backend\DONT_CHANGE\backend_tools\helper_scripts\verify_backend.py strict

If no preset is supplied, "default" is used. The matching
backend_tools\verify_backend_*.bat files are portable Windows starters that
call the helper with their named preset.

Configuring targets and exclusions
----------------------------------

Edit the "Verification settings" section at the top of
backend_tools\helper_scripts\verify_backend.py:

- TARGETS: files or folders to verify, relative to the code folder.
- EXCLUDED_FILES: individual files skipped by Ruff and Pyrefly.
- EXCLUDED_FOLDERS: folders skipped recursively by Ruff and Pyrefly.

Use forward slashes in configured paths. The unfinished backend/DONT_CHANGE/future
folder is excluded by default.

Requirements and exit codes
---------------------------

The verifier uses installed Ruff and Pyrefly when available. Otherwise it runs
them through uvx. At least uv/uvx, or both tools, must be on PATH.

- Exit code 0: every check passed.
- Exit code 1: one or more checks found problems.
- Exit code 2: a required verification tool was unavailable.

Other backend tools
-------------------

- measure_*.bat measures startup, package-import, or file-import performance.
- test_script_wrapper.bat exercises traceback and exit handling in the frontend
  script wrapper.
- standin_main_script.py and helper_scripts support the test and measurement
  launchers.


Future work
===========

The future folder contains unfinished experiments. The current terminal-emulator
idea aims to provide a more app-like terminal with optional input history,
autoscroll controls, script stop/restart controls, system-tray support, print
notifications, close-confirmation controls, a button to open the Python script,
and fine-grained visual settings including dark-mode support.


ASCII font data and licenses
============================

future\ascii_fonts contains FIGlet/TOIlet font files copied from the font data
used by the TAAG Text to ASCII Art Generator:

https://patorjk.com/software/taag/

The fonts have different license statements; treat each file individually.

| File | TAAG font name | Header license/status |
| --- | --- | --- |
| standard.flf | Standard | Header permits modification if the modifier is named in a comment line; retain attribution and verify redistribution terms when needed. |
| coder_mini.flf | Coder Mini | Header says it is free to use and distribute under the MIT License. |
| future.tlf | Future | Header says WTFPL version 2, with no warranty. |
| future_smooth.tlf | Future Smooth | Header says WTFPL version 2, with no warranty and credits the modifications. |

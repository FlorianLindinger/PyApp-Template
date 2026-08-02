DEVELOPER TOOLS
===============

This folder contains shortcuts and configuration files for maintaining the
application's frontend Python environment.


PACKAGE SHORTCUTS
-----------------

The shortcuts can:

- install packages imported by project Python files;
- install packages from a local requirements.txt;
- open a terminal for manual package installation;
- reset or upgrade the frontend Python environment;
- save installed or required package lists; and
- make the current package set the template default.

DEFAULT_PYTHON_PACKAGES.txt contains the default frontend package list used by
the reset/install tools.

MISCELLANEOUS SHORTCUTS
----------------------

miscellaneous/check_longest_paths.lnk scans the project root (excluding .git),
lists the longest paths, and shows the remaining space before the conservative
260-character Windows limit. Press Enter to check again, or close the terminal
to exit. If little space remains, move the project closer to a drive root or
shorten nested names.


FRONTEND VERIFICATION
---------------------

The shortcuts in verify code/ run Ruff linting, Ruff format checks, and
Pyrefly type checking for the frontend targets.

- verify_main_py_basic/default/strict.lnk checks code without changing it.
- fix_and_verify_main_py_basic/default/strict.lnk applies Ruff's safe fixes
  and formatting before it verifies the code.

Each verification terminal clears its previous output before a run. Press
Enter to rescan, or close the terminal window when finished.

Configure frontend verification in:

    ../DONT_CHANGE/settings/backend_settings.py

The relevant settings are FRONTEND_VERIFICATION_TARGETS,
FRONTEND_VERIFICATION_EXCLUDED_FILES,
FRONTEND_VERIFICATION_EXCLUDED_FOLDERS,
FRONTEND_VERIFICATION_VALID_PRESETS, and
FRONTEND_VERIFICATION_DEFAULT_PRESET.

Ruff reads its lint and formatting configuration from ../../pyproject.toml
([tool.ruff]). Pyrefly also looks for a [tool.pyrefly] section in that file,
but none is configured currently; its preset, targets, and exclusions therefore
come from the verification launcher and backend_settings.py.


CAUTION
-------

Package-management tools intentionally change the generated frontend Python
environment. Read the shortcut name before running it. The verify_main_py
shortcuts are read-only; the fix_and_verify_main_py shortcuts modify files
only when Ruff can apply a safe fix or formatting change.


IMPLEMENTATION LAYOUT
---------------------

DONT_CHANGE/scripts/dev_tools/
    Contains the Python implementations.

DONT_CHANGE/B/dev_tools/
    Contains the portable .bat launchers used by the verification shortcuts.

verify code/
    Contains the portable Windows .lnk shortcut entry points.

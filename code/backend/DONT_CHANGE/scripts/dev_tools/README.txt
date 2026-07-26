DEVELOPER TOOL SCRIPTS
======================

This folder contains the Python implementations behind developer utilities for
package management and main.py verification. User-facing shortcuts may point to
these scripts.


MAIN.PY VERIFICATION
--------------------

verify_main_py.py runs three read-only checks:

1. Ruff lint checking
2. Ruff formatting verification
3. Pyrefly type checking

From this folder, run:

    py -3 verify_main_py.py basic
    py -3 verify_main_py.py default
    py -3 verify_main_py.py strict

If no preset is supplied, "default" is used.

The matching verify_main_py_*.bat files in ../../../developer_tools are
portable Windows starters. They contain no verification logic; each uses a
relative path to call verify_main_py.py with its named preset.


CONFIGURING TARGETS AND EXCLUSIONS
----------------------------------

Edit the "Verification settings" section at the top of verify_main_py.py:

    TARGETS
        Files or folders to verify, relative to the code folder.

    EXCLUDED_FILES
        Individual files skipped by Ruff and Pyrefly.

    EXCLUDED_FOLDERS
        Folders skipped recursively by Ruff and Pyrefly.

Use forward slashes in all configured paths. No main.py exclusions are enabled
by default.


REQUIREMENTS AND EXIT CODES
---------------------------

The verifier uses installed ruff and pyrefly commands when available. Otherwise
it runs them through uvx. At least uv/uvx or both tools must be on PATH.

Exit code 0 = every check passed
Exit code 1 = one or more checks found problems
Exit code 2 = a required verification tool was unavailable


PACKAGE UTILITIES
-----------------

The other scripts install, reset, upgrade, and record frontend Python packages.
Run those through their generated developer-tool shortcuts unless you are
working on the backend itself.

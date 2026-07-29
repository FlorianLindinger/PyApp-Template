BACKEND TEST TOOLS
==================

This folder contains diagnostics and test utilities for the template backend.
They are development tools and are not part of normal application startup.


BACKEND VERIFICATION
--------------------

helper_scripts/verify_backend.py runs three read-only checks:

1. Ruff lint checking
2. Ruff formatting verification
3. Pyrefly type checking

From this folder, run:

    py -3 helper_scripts/verify_backend.py basic
    py -3 helper_scripts/verify_backend.py default
    py -3 helper_scripts/verify_backend.py strict

If no preset is supplied, "default" is used.

The matching verify_backend_*.bat files in this folder are portable Windows
starters. They contain no verification logic; each uses a relative path to call
helper_scripts/verify_backend.py with its named preset.


CONFIGURING TARGETS AND EXCLUSIONS
----------------------------------

Edit the "Verification settings" section at the top of
helper_scripts/verify_backend.py:

    TARGETS
        Files or folders to verify, relative to the code folder.

    EXCLUDED_FILES
        Individual files skipped by Ruff and Pyrefly.

    EXCLUDED_FOLDERS
        Folders skipped recursively by Ruff and Pyrefly.

Use forward slashes in all configured paths. The unfinished
backend/DONT_CHANGE/future folder is excluded by default.


REQUIREMENTS AND EXIT CODES
---------------------------

The verifier uses installed ruff and pyrefly commands when available. Otherwise
it runs them through uvx. At least uv/uvx or both tools must be on PATH.

Exit code 0 = every check passed
Exit code 1 = one or more checks found problems
Exit code 2 = a required verification tool was unavailable


OTHER TOOLS
-----------

measure_*.bat
    Measure startup, package-import, or file-import performance.

test_script_wrapper.bat
    Exercise traceback and exit handling in the frontend script wrapper.

standin_main_script.py and helper_scripts/
    Supporting files used by the test and measurement launchers.

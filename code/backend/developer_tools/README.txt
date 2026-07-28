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

CURRENT_PYTHON_VERSION.txt records the generated frontend interpreter version.


MAIN.PY VERIFICATION STARTERS
-----------------------------

The verify_main_py_*.lnk files are portable shortcuts to the launchers under
DONT_CHANGE/scripts/dev_tools/entry_points. Their relative link information
keeps them working when the project folder moves.

Implementation documentation is located at:

    ../DONT_CHANGE/scripts/dev_tools/README.txt


CAUTION
-------

Package-management tools intentionally change the generated frontend Python
environment. Read the shortcut name before running it. Verification tools are
read-only and do not modify source files.


IMPLEMENTATION LAYOUT
---------------------

scripts/
    Contains the Python implementations.

entry_points/
    Contains one matching .bat entry point for every Python implementation,
    plus the basic/default/strict main.py verification variants. The batches are
    based on entry_points/_batch_template.bat.

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

The verify_main_py_*.bat files are portable, relative-path starters. They call
the verification Python file under DONT_CHANGE/scripts/dev_tools without
storing an absolute path, so moving the project folder does not break them.

Implementation documentation is located at:

    ../DONT_CHANGE/scripts/dev_tools/README.txt


CAUTION
-------

Package-management tools intentionally change the generated frontend Python
environment. Read the shortcut name before running it. Verification tools are
read-only and do not modify source files.

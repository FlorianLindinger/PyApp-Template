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


MISCELLANEOUS SHORTCUTS
----------------------

miscellaneous/check_longest_path.lnk scans the repository (excluding .git
metadata), reports its longest file or folder path, and shows the remaining
space before the conservative 260-character legacy Windows path limit.

The 260-character limit is still relevant because long-path support is not
used consistently by every Windows application, library, archive tool, or
shell integration. Even when Windows long paths and Git long paths are
enabled, keeping project paths comfortably below this limit is the most
portable option.

PATH-LENGTH FAILURE EXAMPLES
----------------------------

Long paths can fail before Python code runs. Common cases include:

- copying or moving the project in File Explorer, especially to a deeper
  destination such as a Desktop, OneDrive, or backup subfolder;
- extracting a ZIP archive whose archive name, extraction destination, and
  nested contents combine into a path that is too long;
- cloning, checking out, or switching Git branches when the destination folder
  is deeply nested or a branch introduces longer file names;
- creating virtual environments, installing packages, or unpacking generated
  dependencies with deeply nested package files; and
- tools that create temporary files below an already-long project path.

If the check reports little remaining space, move the repository closer to a
drive root (for example C:\src\PyApp-Template), shorten deeply nested names,
and avoid placing generated Python environments inside a long project path.


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

DEVELOPER TOOLS
===============

Run the .bat files in this folder to maintain the application's Python and
packages. Each batch calls its matching DONT_CHANGE/scripts/dev_tools/*.py
through the shared backend bootstrap/runner; no generated shortcuts are needed.
Paths are relative to the batch file, so these tools work after moving the project.

DEFAULT_PYTHON_PACKAGES.txt is the shared default dependency list. The adjacent
.lock.json and determined/auto-found package lists are generated local state.

PACKAGE ACTIONS
---------------

install_imports.bat              Infer/review dependencies from project imports.
install_local_reqs.bat           Install requirements.txt from this folder.
open_package_terminal.bat        Open a terminal using the application Python/pip.
reset_packages_default.bat       Replace installed packages with the defaults.
reset_packages_empty.bat         Remove installed application packages.
reset_packages_imports.bat       Replace packages with inferred dependencies.
upgrade_packages.bat            Upgrade installed application packages.
save_current_packages_*.bat      Save installed package names or versions here.
save_imported_packages_*.bat     Save inferred requirements here.
set_default_packages_*.bat       Make current packages the default dependency list.

Package actions can change the generated Python/package environment. Read the
batch name before running it. Python implementations report failures through the
shared runner and preserve nonzero exit codes. Successful interactive tools wait
when configured to do so.

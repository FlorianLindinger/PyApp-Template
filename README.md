# 🐍 PyApp-Template

**Template for a Windows-only, easily-shareable, self-environment-controlled, source-code-running, ready-to-use (just insert your python file), plug-and-play python application** 

---

# Main Features

- Self-contained, fully version controlled, git-sharable, idiot-proof python environment with automatic download of python & needed packages at user end (no installation needed by end user).
- Structured in a way to make it easily shareable/runnable even with people without any coding/PC experience (plug-and-play).
- Ready to use: Just insert your python code file.
- Ready to use settings file (yaml or python) for user interaction with shortcuts to the settings file and improved yaml file variable interpretation which allows a more pythonic way to define variables (simple math operations and scientific notations).
- Fully accessable/modifyable python source code file. while having the convenience of an executable but without the wait time for compilation.
- Quality of life features for python environment managment (under code/python_environment_code: Environment reset, pip-install-launcher, saving of current packages, auto-installing packages needed in python files.
- Fully ready for git repositories to only share the needed parts and don't sync generated files or downloaded packages.
- Instructions and utilities to generate proper icon files from images.
- Option to change icon and title and colors of the python-launched terminal.
- Automatic generation of shortcuts with icons that can be added to the taskbar.
- Option for no-terminal execution with stop-button and logging (print & errors) to file.
- Automatic handling of python crashes with the option to restart the main file or executing and crash-handling python file.
- Feel free to suggest more :)

---

## Quick Start

1. Clone/download this repository
2. Add the python code you want to execute to "code/main_code.py"
3. Run "code/python_environment_code/install_packages_needed_in_python_files.lnk" to install all packages your python file needs
4. (Optional: Change program-settings under "code/non-user_settings.ini")
5. (Optional: Add user-settings under "code/python.yaml")
6. Execute RUN_BEFORE_FIRST_START_TO_GENERATE_SHORTCUTS.lnk
7. Run program via the generated shortcuts 

---

## Work in Progress

- Utilities like safer folder deletion.
- Template and boilerplate code for a GUI using PyQt5.
- Plug-and-play license template & handling of non-distributables via .gitignore & a permissive MIT license for my codes.
  
---

## Notes

Tested to work in current Windows 11 Home/Pro

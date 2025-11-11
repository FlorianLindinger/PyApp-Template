# 🐍 PyApp-Template

**Template for a Windows-only, offline portable & git-shareable, source-code-running, 100%-isolated, ready-to-use (just insert Python file), full-version (aka. non-embedded) Python application** 

---

# Main Features

- Full-version Python. Usually portable Python entails the embeddable version which lacks some vanilla Python features (which are for example needed for default matplotlib). This template avoids that by making the full version and the virtual environment portable without bloated third party solutions.
- Portable folder that can be shared offline after a setup execution.
- 100%-isolated. Usually full python uses a globally installed python.exe, even for virtual environments. This template avoids that and doesn't mess with anything global.
- No prior installation required. Python and packages are automatically installed.
- Automatic minimal size git-shareable with ready .gitignore file that prevents sharing of unlicensed, python distribution, and package files, that are auto downloaded/copied at user end.
- Ready to use: Just insert your python code file and optionally quickly change settings like python version or app name.
- Ready-to-use settings file (yaml or python) for user interaction with shortcuts to the settings file and improved yaml file variable interpretation which allows a more pythonic way to define variables (simple math operations and scientific notations).
- Runs fully accessible source code. This template makes python files behave effectively as if they were compiled with an included python environment while remaining 100% accessible, avoiding compilation time, and not making user modifications more complex.
- Quality of life features for python environment managment (under code/python_environment_code: Environment reset, pip-install-launcher, saving of current packages, auto-installing packages needed in python files,...)
- Instructions and utilities to generate proper icon files from images and automatic inclusion in the shortcuts
- Option to change icon and title and colors of the python-launched terminal.
- Automatic generation of shortcuts with icons that can be added to the taskbar. Usually it is not possible to have multiple shortcuts on the taskbar with custom icons that launch python/batch files. This template has workarounds
- Option for no-terminal execution with stop-button and logging (print & errors) to file.
- Automatic handling of python crashes with the option to restart the main file or execute a crash-handling python file.
- Wrapper code built with modular single-function batch files that enable reuse of code parts and easier modification.
- Includes template files for good practice python projects like readmes, pyproject.toml, license, version, Todo,...
- Small launch overhead of all features: ~+0.2 s (global python is ~0.15 s)
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

Tested to work in current Windows 11 Home/Pro and Python 3.13

# 🐍 PyApp-Template

**Template for a Windows-only, offline portable & git-shareable, source-code-running, 100%-isolated, ready-to-use (just insert Python file), full-version (aka. non-embedded) Python (3.7+) application**

---

## Main Features

- **Full-version Python**: Usually portable Python entails the embeddable version which lacks some vanilla Python features (which are for example needed for default matplotlib). This template avoids that by making the full version and the virtual environment portable without bloated third party solutions.
- **Portable** folder that can be shared offline after a setup execution.
- **100%-isolated**. Usually full python uses a globally installed python.exe, even for virtual environments. This template avoids that and doesn't mess with anything global.
- **No prior Python installation required**. Python and packages are automatically installed.
- **Minimal size** (~10 MB) and **git-shareable** with .gitignore files that prevents sharing of (unlicensed) python distribution and package files, that are auto downloaded at user end.
- Ready to use: **Just insert your python code file** and optionally quickly change settings like python version or app name.
- **Ready-to-use settings file** (many file formats available) for user interaction with shortcuts to the settings file and improved string conversion to floats (simple math operations and scientific notations).
- **Runs fully accessible source code**. This template makes python files behave effectively as if they were compiled with an included python environment while remaining 100% accessible, avoiding compilation time, and not making user modifications more complex.
- **Quality of life features for python environment managment** (under code/dev_tools: Environment reset, pip-install-launcher, saving of current packages, auto-installing packages needed in python files,...)
- Instructions and **utilities to generate proper icon files** from images and automatic inclusion in the shortcuts
- Option to **change icon, title, and colors** of the python-launched **terminal**.
- Automatic generation of **shortcuts** with icons that **can be added to the taskbar**. Usually it is not possible to have multiple shortcuts on the taskbar with **custom icons** that launch python/batch files.
- **Option for no-terminal execution with stop-button and logging** (print & errors) to file.
- Automatic **handling of python (interpreter) crashes** with the option to restart the main file or execute a crash-handling python file.
- Includes **template files** for good practice python projects **like pyproject.toml**, readmes, license, version, Todo,...
- **Small launch overhead** of all features: ~+0.2 s (global python start is ~0.15 s)
- Options to **install only needed parts of full-Python** installation (down to ~48 MB instad of ~150 MB for normal python installations)
- Plug and play **license template**, where all backend template code parts fall under the **permissive MIT license** and non-MIT parts are auto-excluded via .gitignore. and generated at the user end.
- Feel free to suggest more :)

---

## Quick Start

1. Clone/download/copy this repository
2. Add the python code you want to execute to `code/main_code.py`
3. Run `code/dev_tools/install_packages_needed_in_python_files.lnk` to install all packages your python file needs
4. (Optional: Change program-settings like Python version or program name under `code/non-user_settings.ini`)
5. (Optional: Add user-settings under `code/python.{file-ending}`)
6. Execute `RUN BEFORE FIRST START TO GENERATE SHORTCUTS.lnk` to generate shortcuts
7. Run program via the generated shortcuts

---

## Work in Progress

- Template and boilerplate code for a GUI using PyQt5.
- Many small improvements and feature ideas.

---

## Notes

Tested to work in current Windows 11 Home/Pro and Python 3.13. This repository was originally built by Florian Lindinger and can be accessed under https://github.com/FlorianLindinger/PyApp-Template
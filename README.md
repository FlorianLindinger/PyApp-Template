# 🐍 PyApp-Template

**Template for a Windows-only, offline portable & git-shareable, source-code-running, 100%-isolated, ready-to-use (just insert Python file/code), full-version (aka. non-embedded) Python (3.7+) application that does not require end-users to have any Python experience**

---

## Main Features

- **Full-version Python**: Usually portable Python entails the embeddable version which lacks some vanilla Python features (which are for example needed for default matplotlib). This template avoids that by making the full version and the virtual environment portable without bloated third party solutions.
- **Portable** folder that can be shared offline after first setup execution.
- **100%-isolated**. Usually full python uses a globally installed python.exe, even for virtual environments. This template avoids that and doesn't mess with anything global.
- **No prior Python installation required**. Python and packages are automatically installed.
- **Pretty small size** (~120 MB) and **git-shareable** with .gitignore files that prevents sharing of (potentially unlicensed) python distribution and package files, that are auto downloaded at user end.
- Ready to use: **Just insert your python code file** and optionally quickly change settings like python version or app name.
- **Runs fully accessible source code**. This template makes python files behave effectively as if they were compiled with an included python environment while remaining 100% accessible, avoiding compilation time, and simplifying end-user modifications.
- **Quality of life features for python environment management** (under `code/developer_tools`: environment reset, pip-install launcher, saving current packages, auto-installing packages needed in Python files, ...)
- Automatic generation of **icons from a png**.
- Options to **change icon, title, and colors** of the python-launched **terminal**.
- Automatic generation of **shortcuts with icons** that **can be added to the taskbar**. Usually it is not possible to have multiple shortcuts on the taskbar with **custom icons** that launch python/batch files.
- If the starting shortcut is in the taskbar, it will group the opened terminal/GUI with that shortcut. This avoids taskbar spamming and overlooking that App is already opened.
- **Option for no-terminal execution with stop-button and logging** (print & errors) to file.
- Automatic **handling of code & python interpreter crashes** with the option to restart the main file or execute a crash-handling python file.
- **Small launch overhead** of all features: ~+0.2 s (global python start is ~0.15 s)
- Plug and play **license template**, where all backend template code parts fall under the **permissive licenses**.
- Avoids opaque executables to minimize antivirus false positives that compiled python code can suffer from.
- Option for fancy modern professional looking terminal emulator with many features like minimization to system tray or eixt confirmation prompt (see below).
- Option to save prints/errors in log files.
- Option to add timestamps to prints and logging.
- Feel free to suggest more :)

---

## Quick Start

1. Clone/download/copy this repository
2. Add the python code you want to execute to `code/main_code.py`
3. (Optional: Change program settings like Python version or program name under `code/developer_settings.py`)
4. (Optional: Add user settings under `code/settings.py`)
5. Execute `RUN BEFORE FIRST START AND AFTER FOLDER MOVE TO GENERATE SHORTCUTS.lnk` to generate shortcuts
6. Run program via the generated shortcuts (it will auto install needed packages)

---

## Optional Terminal Emulator - Features

- TODO

---

## Notes

Tested to work in current Windows 11 Home/Pro and Python 3.14. This repository was originally built by Florian Lindinger and can be accessed under https://github.com/FlorianLindinger/PyApp-Template

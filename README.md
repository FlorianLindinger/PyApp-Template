# 🐍 PyApp-Template

**Backend template for a Windows-only, offline portable & git-shareable, source-code-running, 100%-isolated, ready-to-use (just insert Python file/code), full-version (aka. non-embedded) Python (3.5+) application that does not require end-users to have any Python experience**

---

## Main Features

- **Full-version Python**: Usually portable Python entails the embeddable version which lacks some vanilla Python features (which are for example needed for default matplotlib). This template avoids that by making the full version and the virtual environment portable without bloated third party solutions.
- **Portable** folder that can be shared offline after first setup execution.
- **100%-isolated**. Usually full python uses a globally installed python.exe, even for virtual environments. This template avoids that and doesn't mess with anything global.
- **No prior Python installation required**. Python and packages are automatically installed.
- **Minimal Git size and license-safe Git sharing**: Python runtimes, virtual environments, and third-party Python packages are not meant to be committed. They are excluded by `.gitignore` and installed/generated on the user's machine, keeping the repository source-focused and avoiding accidental Git distribution of bulky or separately licensed dependency files.
- **Fast package installation with uv support**: package installs use `uv` by default when globally available or installs it into the repository locally if not disabled in settings. It can benefit from uv's global cache across projects.
- Ready to use: **Just insert your python code file** and optionally quickly change settings like python version or app name.
- **Runs fully accessible source code**. This template makes python files behave effectively as if they were compiled with an included python environment while remaining 100% accessible, avoiding compilation time, and simplifying end-user modifications.
- **Quality of life features for python environment management** (under `code/dev_tools`: environment reset, pip-install launcher, saving current packages, auto-installing packages needed in Python files, ...)
- Automatic generation of **icons from a png**.
- Options to **change icon, title, and colors** of the python-launched **terminal**.
- Automatic generation of **shortcuts with icons** that **can be added to the taskbar**. Usually it is not possible to have multiple shortcuts on the taskbar with **custom icons** that launch python/batch files.
- If the starting shortcut is in the taskbar, it will group the opened terminal/GUI with that shortcut. This avoids taskbar spamming and overlooking that App is already opened.
- **Option for no-terminal execution with stop-button and logging** (print & errors) to file.
- Automatic **handling of code & python interpreter crashes** with the option to restart the main file or execute a crash-handling python file.
- **Small launch overhead** of all features: ~+0.2 s (global python start is ~0.15 s)
- Plug-and-play **license template** with the template-owned backend available under the permissive `MIT OR Apache-2.0` dual license.
- Avoids opaque executables to minimize antivirus false positives that compiled python code can suffer from.
- Choice to have the working directory be the script folder or the shortcut folder.
- Option to save prints/errors in log files.
- Option to add timestamps to prints and logging.
- Feel free to suggest more :)

---

## Quick Start

1. Clone/download/copy this repository
2. Add the python code you want to execute to `code/main.py`
3. (Optional: Change program settings like Python version or program name under `code/backend/developer_settings.py`)
4. (Optional: Add user settings under `code/settings.py`. Import them in `main.py` via `import settings`)
5. Execute `▶️ RUN BEFORE FIRST START AND AFTER FOLDER MOVE TO GENERATE SHORTCUTS.cmd` to generate shortcuts
6. Run program via the generated shortcuts (it will auto install needed packages)

The leading `▶️` is a portable play-button marker in the filename. The launcher itself remains a fully reviewable batch file and resolves the repository folder from its own location, so moving the repository does not break it.

---

## Project Structure

```text
.
├── code/                              Application source and local runtime files
│   ├── main.py                        Main application entry point — edit this
│   ├── settings.py                    Application settings — edit as needed
│   ├── backend/
│   │   ├── developer_settings.py      Backend/development preferences
│   │   └── DONT_CHANGE/               Template launcher internals
│   │       ├── settings/              Backend Python version, paths, and package lists
│   │       ├── scripts/               Setup, launch, shortcut, and helper scripts
│   │       ├── backend_tools/         Verification and performance tools
│   │       ├── backend_python/        Generated embedded launcher runtime
│   │       └── backend_packages/      Generated launcher dependencies
│   ├── dev_tools/                     Development and package-management tools
│   ├── icons/                         Application icon source/output files
│   ├── python/                        Generated full frontend Python runtime
│   ├── packages/                      Generated frontend Python packages
│   └── pyproject.toml                 Development-tool configuration
├── logs/                              Generated program logs
├── crash logs/                        Generated crash reports
├── *.lnk                              Generated Windows launch shortcuts
└── README.md                          This overview
```

Edit `code/main.py`, `code/settings.py`, and `code/backend/developer_settings.py`
for normal project work. The `python`, `packages`, `backend_python`,
`backend_packages`, `logs`, and `crash logs` folders are generated locally and
are intentionally excluded from normal Git tracking.

`code/backend/DONT_CHANGE` contains the portable launcher implementation. Its
[own README](code/backend/DONT_CHANGE/README.txt) explains the installation
flow, backend settings, safety checks, package lists, diagnostics, and licensing
in detail.

---

## Notes

Tested to work in current Windows 11 Home and Python 3.14. This repository was originally built by Florian Lindinger and can be accessed under https://github.com/FlorianLindinger/PyApp-Template

---

## Licensing

The template-owned backend files in `code/backend/DONT_CHANGE` are available under your choice of the MIT License or Apache License 2.0 (`MIT OR Apache-2.0`). Python distributions and third-party packages retain their own licenses and are excluded from normal Git tracking.

Projects created from this template must replace the project-license placeholder in [`LICENSE.md`](LICENSE.md) with their chosen license. See that file for the complete scope and third-party exceptions.

# 🐍 PyApp-Template

Turn a Python script or Tkinter app into a portable Windows x64 application.
Users launch a shortcut; the template manages a local Python runtime, dependencies,
logs, and crash reports. They do not need Python installed.

Start with the included GUI example in `code/main.py`, then replace it with
your own code. A prepared folder can be copied and used offline.

---

## Main Features

- **Full Python runtime** with optional Tkinter support for applications that need standard GUI modules. The small embedded backend is separate from the runtime used by your app.
- **Portable** folder that can be shared offline after first setup execution.
- **Local Python and package environments**. Managed launches ignore Python environment overrides and user-site packages. Package tools target the local environment. This is dependency isolation, not an operating-system security sandbox; application code still has your normal user permissions.
- **No prior Python installation required**. Python and packages are automatically installed.
- **Minimal Git size and license-safe Git sharing**: Python runtimes, virtual environments, and third-party Python packages are not meant to be committed. They are excluded by `.gitignore` and installed/generated on the user's machine, keeping the repository source-focused and avoiding accidental Git distribution of bulky or separately licensed dependency files.
- **Fast package installation with uv support**: package installs use `uv` by default when globally available or installs it into the repository locally if not disabled in settings. It can benefit from uv's global cache across projects.
- Ready to use: **Just insert your python code file** and optionally quickly change settings like python version or app name.
- **Runs fully accessible source code**. This template makes python files behave effectively as if they were compiled with an included python environment while remaining 100% accessible, avoiding compilation time, and simplifying end-user modifications.
- **Quality of life features for python environment management** (under `code/backend/dev_tools`: environment reset, pip-install launcher, saving current packages, auto-installing packages needed in Python files, ...)
- Automatic generation of **icons from a png**.
- Options to **change icon, title, and colors** of the python-launched **terminal**.
- Automatic generation of **shortcuts with icons** that **can be added to the taskbar**. Usually it is not possible to have multiple shortcuts on the taskbar with **custom icons** that launch python/batch files.
- If the starting shortcut is in the taskbar, it will group the opened terminal/GUI with that shortcut. This avoids taskbar spamming and overlooking that App is already opened.
- **Option for no-terminal execution with stop-button and logging** (print & errors) to file.
- Automatic **handling of code & python interpreter crashes** with visible diagnostics and package-recovery restart options.
- **Startup health checks** validate the runtime and installed package records. Use the included benchmark to measure overhead on your machine; older timing estimates predate these checks.
- Plug-and-play **license template** with the template-owned backend available under the permissive `MIT OR Apache-2.0` dual license.
- Avoids opaque executables to minimize antivirus false positives that compiled python code can suffer from.
- Choice to have the working directory be the script folder or the shortcut folder.
- Option to save prints/errors in log files.
- Option to add timestamps to prints and logging.
- Feel free to suggest more :)

---

## Quick Start

1. Clone/download/copy this repository
2. Try the Tkinter GUI example in `code/main.py`, or replace it with your application
3. (Optional: Change program settings like Python version or program name under `code/backend/developer_settings.py`)
4. (Optional: Add user settings under `code/settings.py`. Import them in `main.py` via `import settings`)
5. Execute `Setup.cmd` (or the play-button `.cmd` alias) to validate/setup the environments and generate shortcuts
6. Run `Start.cmd` or a generated shortcut. Declare dependencies in `code/backend/dev_tools/change python packages/DEFAULT_PYTHON_PACKAGES.txt`; they are installed transactionally. Import inference is an optional, reviewed developer action.

`Setup.cmd` and `Start.cmd` resolve the repository from their own locations. After moving the folder, run `Setup.cmd` to refresh generated shortcuts. The play-button `.cmd` is an alias for setup.

---

## Project Structure

```text
.
├── code/
│   ├── main.py                        <<< MAIN APP CODE: EDIT THIS
│   ├── settings.py                    <<< END-USER SETTINGS: EDIT AS NEEDED
│   └── backend/
│       ├── developer_settings.py      <<< APP / PYTHON SETTINGS
│       ├── dev_tools/                 <<< DEVELOPMENT TOOLS
│       ├── icons/                     <<< ICON SOURCE & GENERATION TOOLS
│       ├── DONT_CHANGE/               Template internals (see its README)
│       └── ...                        Self explanatory folders   
├── logs/                              Generated program logs
├── crash logs/                        Generated crash reports
```

Edit `code/main.py`, `code/settings.py`, and `code/backend/developer_settings.py`
for normal project work. The `python`, `packages`, `backend_python`,
`backend_packages`, `logs`, and `crash logs` folders are generated locally and
are intentionally excluded from normal Git tracking.

`code/backend/DONT_CHANGE` contains the portable launcher implementation. Its
[own README](code/backend/DONT_CHANGE/README.md) explains the installation
flow, backend settings, safety checks, package lists, diagnostics, and licensing
in detail.

---

## Notes

Tested to work in current Windows 11 Home and Python 3.14. This repository was originally built by Florian Lindinger and can be accessed under https://github.com/FlorianLindinger/PyApp-Template

---

## Licensing

The template-owned backend files in `code/backend/DONT_CHANGE` are available under your choice of the MIT License or Apache License 2.0 (`MIT OR Apache-2.0`). Python distributions and third-party packages retain their own licenses and are excluded from normal Git tracking.

Projects created from this template must replace the project-license placeholder in [`LICENSE.md`](LICENSE.md) with their chosen license. See that file for the complete scope and third-party exceptions.

## Arguments, isolation, and dependency updates

`args_for_main_py` in `developer_settings.py` configures the arguments passed to
`main.py`. Generated shortcuts and `Start.cmd` do not forward additional command-line
arguments to the application. Launcher state such as terminal mode is never added
to `main.py`'s positional arguments.

`Start.cmd` uses its own folder as the launch folder; generated shortcuts set
Start in to the repository root. Set a shortcut's Start in directory explicitly
when using `start_in_shortcut_folder=True`. Relative-to-launch log paths use
the same captured directory even after backend setup changes its working directory.

The supported managed platform is **Windows x64 (AMD64)**. Native ARM64 and
32-bit runtime installation are not implemented. The installer rejects those
architectures before downloading/replacing a runtime. Python 3.5+ compatibility
is retained in the frontend wrapper, but the regression suite currently covers
the locally available Python 3.12, 3.13, and 3.14 interpreters.

Managed and global launches use `-E -s`: `PYTHONHOME`, `PYTHONPATH`, and user-site
packages do not affect them. Global mode resolves one actual interpreter and
does not automatically modify it. Missing-package errors show its path and a
manual command; the local environment is not modified as a substitute.

The template records exact runtime selection in `code/backend/frontend-python.lock.json`
and resolved default packages in `DEFAULT_PYTHON_PACKAGES.txt.lock.json` beside
the requirements file. Commit these files with a release. Changing requirements
(including local `-r`/`-c` includes) invalidates its package lock. Deliberately
remove the appropriate lock to request fresh resolution. Locks pin versions;
they are not a promise that third-party source builds are bit-for-bit identical
or that removed external artifacts will remain downloadable. Preserve a prepared
folder for an offline distribution.

## Logs and diagnostics

Each run has its own directory under `code/backend/DONT_CHANGE/temporary/runs/`.
Logs receive a unique run suffix. The normal UTF-8 log records Python text/input
and atexit callbacks; its `.output.log` companion captures raw combined stdout
and stderr, including binary writes and inherited child-process output. With
logging enabled stdout/stderr are pipes, so applications that require a real
terminal should disable logging for their terminal launch. Detached subprocesses
that redirect their own output are outside this capture.

Successful runs do not create crash reports. Hidden successful runs remain hidden
when `close_after_success=True`. Failures preserve their diagnostics. Persistent
MSI logs are under `temporary/installation-logs/`; failed backend staging folders
are retained with their diagnostic files. These folders can grow and are not
currently pruned automatically.

## Tkinter example and Stop

The example in `code/main.py` opens a small window displaying "Example GUI".
The launcher sets `PROGRAM_NAME` and `ICON_PATH` environment variables from the
project settings. The example reads these for its window title and icon, without
importing backend settings. Running it directly uses the title "Example GUI"
and Tkinter's default icon unless these variables are set.
`PROGRAM_HAS_TERMINAL` is also set to `"1"` for terminal launches and `"0"` for
hidden launches. Check it with `os.environ.get("PROGRAM_HAS_TERMINAL") == "1"`.
Replace it with your own application.

Stop directly terminates the verified application process tree. It does not run
application cleanup callbacks.

PID records exist only while instances are registered. Closing the last instance
or using Stop removes the empty PID registry folder and legacy PID/lock files.
If the watchdog itself is forcibly killed, stale records are cleaned on the next
launch or Stop. Registry synchronization uses a Windows mutex, not a disk lock file.

# Linux builds from Windows (WSL)

Only your configured main script and its Python dependencies are compiled. The Windows launcher,
tray, browser console and its supervision/settings are not embedded or ported to Linux.
The resulting program runs on compatible Linux systems without a separately installed Python.
Windows-only imports and dependencies in your app still need Linux alternatives or platform guards.

To only see the app run on Linux (no build), use *test-linux* in the developer tools.

1. If Ubuntu is not installed: open an **administrator** Windows terminal and run
   `"Open Developer Tools Menu.cmd" setup-linux --install-wsl` in `code\pyapp`. Restart Windows if requested; start Ubuntu once and finish
   its user/password setup. This uses [Microsoft's WSL installation](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).
2. Run *setup-linux* in Compilation Tools. This installs
   `build-essential`, `patchelf`, `python3`, `curl`, `ca-certificates`, and `git` through Ubuntu's apt;
   sudo can ask for your Ubuntu password. These build prerequisites remain installed.
3. Edit `linux_settings.json`. It uses the same options and the [editable presets](presets.json) as Windows compilation,
   with an independent configuration. Default: standalone folder, terminal variant. Windows-only
   options such as `--msvc`, `--mingw` and `--windows-*`, and the `gui`/no-terminal variant, are rejected.
   A Linux GUI app can still be built with its Qt/Tk plugins; desktop launch behavior is a separate concern.
4. Run *compile-linux* in Compilation Tools. The result goes to `code/pyapp/compiled/linux/<preset>/`.

Examples, from a terminal in `code\pyapp`:

```bat
"Open Developer Tools Menu.cmd" compile-linux --dry-run
"Open Developer Tools Menu.cmd" compile-linux --preset development
"Open Developer Tools Menu.cmd" compile-linux --mode onefile
"Open Developer Tools Menu.cmd" compile-linux --distribution Ubuntu-22.04
"Open Developer Tools Menu.cmd" setup-linux --distribution Ubuntu-22.04
```

The default WSL distribution is `Ubuntu`; `--distribution` selects another installed Ubuntu/Debian
WSL distro. Setup uses apt, so other Linux families require their own prerequisite installation.
If WSL itself is unavailable, enable the Windows Subsystem for Linux feature first.
Dry runs validate settings and print the selection; they do not start WSL, install packages or build.

The worker bootstraps [uv](https://docs.astral.sh/uv/reference/installer/) in a user-owned Linux cache
without editing shell profiles. uv obtains the `python_version` from `developer_settings.py` and
installs Linux versions of `packages` plus `requirements_path` into a disposable Linux environment.
It resolves for Linux independently of the Windows environment and Windows `uv.lock`; pin requirements
and use environment markers when different platforms need different dependencies. Requirements files
are interpreted by Linux uv, so their paths/options must be Linux-compatible. Relative paths resolve
from the code folder. Data inclusion sources are mapped from Windows to WSL automatically; destinations
should use Linux forward slashes. Other custom path-bearing extra arguments must use Linux paths.

Nuitka, ordered-set and zstandard are installed temporarily in the disposable environment, constrained
against the resolved app versions. The whole build environment is removed on success or failure/handled
interruption. A force-killed worker can leave scratch data under `~/.cache/pyapp-compilation/build-*`.
Downloaded uv, Python and package/compiler caches remain available for faster later builds.
The Windows environment and lock file are unchanged.

Compilation uses Linux storage for intermediate files. Results appear in
`code/pyapp/generated/compilation/linux/<preset>/<mode>/`:

- `<app>-linux-<architecture>.tar.gz`: complete standalone `.dist` folder or the onefile `.bin`.
  Transfer this archive and extract **on Linux** with `tar -xzf <archive>` to preserve executable bits
  and symlinks. For standalone mode, keep the entire extracted folder together.
- `compilation-report.xml`: Nuitka diagnostic report, also copied after a failed build if available.
- `linux-requirements.txt`: resolved app package versions before temporary build tools are added.
- `build-info.json`: build platform, architecture, requested Python version and compiler command.

Build on the **oldest Linux distribution you intend to support**: binaries linked against a newer
Linux/glibc may not run on older distributions. CPU architecture also needs to match. Onefile still
extracts its bundled components at startup; standalone avoids that extraction. Test the produced
archive on your actual target Linux systems. These tools never run your app automatically.
*clean-compilation* removes the returned Windows-side artifacts, while Linux download caches remain.

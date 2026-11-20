# Compilation tools

Double-click **Compilation Tools.cmd** in this folder (or choose *compilation* in
`Open Developer Tools Menu.cmd`). Compilation is optional; normal app starts never use it.

This folder holds only settings: `settings.json` (which preset to build), `presets.json` (the
presets) and `linux_settings.json` (the Linux build). They belong to your app; commit them.
The builds go to `code/pyapp/compiled/windows/<preset>/` and `code/pyapp/compiled/linux/<preset>/`,
which Git ignores. Each build replaces the previous build of the same preset completely, so no
old file stays behind; `--keep` builds into a new folder with the date and time instead.

## What happens

1. Read the selected preset/settings. Invalid settings stop before environment preparation.
2. Use the project's managed Python and `main_script_path` from `developer_settings.py`.
3. Check app source syntax without executing it. The separate *validate-syntax* tool stops here.
4. Make Nuitka/build helpers available temporarily, then run Nuitka: analyze imports,
   generate native code and invoke a C compiler. Plugins and
   explicit inclusions help it find dynamically loaded packages and resource files.
5. Write artifacts and an XML report to `code/pyapp/compiled/windows/<preset>/` (a changed mode
   or console is added to the folder name, e.g. `gui-onefile-terminal`).
   Remove temporary compiler packages on completion or failure. The app is **not launched**
   automatically; test it on a clean target machine.

This builds the **app entry script**, not the complete PyApp launcher. Logging, tray controls,
the browser terminal, recovery, Stop shortcuts and developer settings are not automatically
embedded. A compiled GUI needs its own diagnostics. Compilation does not protect embedded secrets.
`args_for_main_py` and `environment_for_main_py` are launch settings, not compiler options:
provide the required runtime arguments/environment when starting the executable.

## Presets

Edit **settings.json** to choose the default; edit **presets.json** to customize/add presets.
Both belong to your app and survive replacing `DONT_CHANGE`. Preset names use lowercase
letters, numbers, hyphens or underscores.

| Preset | Result | Use |
| --- | --- | --- |
| `development` | Console + standalone folder; unbuffered Python output | Integrating packages/resources and diagnosing failures |
| `standalone` | Console + standalone folder | Recommended first distribution; copy the **whole `.dist` folder** |
| `onefile` | Console + single executable | Convenience distribution after standalone works; extracts its payload on startup |
| `gui` | Standalone folder without a console | A GUI app that handles its own diagnostics |

Normal Python checks and Nuitka's standard compiler/cache choices stay enabled. These are not
antivirus-safe or performance guarantees. Cleanup removes marked project output and preserves
shared compiler caches.

## Settings to supply

| Setting | Value / when to change it |
| --- | --- |
| `preset` | Start with `"standalone"`; use `"gui"` for an app that needs no console |
| `mode` | `null` keeps the preset; `"standalone"` or `"onefile"` overrides it |
| `variant` | `null` keeps the preset; `"terminal"` or `"no_terminal"` overrides it |
| `jobs` | `null` lets Nuitka choose parallelism; a positive integer caps build jobs |
| `unbuffered` | `null` keeps the preset; `true` writes Python stdout/stderr immediately |
| `plugins` | Nuitka plugins, e.g. `["pyside6"]` if the app uses PySide6; otherwise empty |
| `include_packages` | Packages loaded dynamically, e.g. `["my_plugins"]`; normal imports are analyzed automatically |
| `include_package_data` | Package resource data not otherwise discovered, e.g. `["my_package"]` |
| `include_data_files` | File mappings, e.g. `["assets/defaults.json=assets/defaults.json"]` |
| `include_data_dirs` | Whole data directories, e.g. `["assets=assets"]` |
| `extra_args` | Additional Nuitka arguments; leave empty until a specific need appears |

Resource source paths start at `code`; destinations are inside the distribution. Do not include
unused packages/plugins. Python files and DLLs are code, not data files. In onefile builds,
`__file__` points inside the extracted payload; `sys.argv[0]` identifies the executable.
Mutable user settings should usually remain outside the bundled payload.

A PySide6 GUI with an assets folder would change only these fields in the shipped settings:

```json
{
  "preset": "gui",
  "plugins": ["pyside6"],
  "include_data_dirs": ["assets=assets"]
}
```

Keep the other fields unchanged. Do not use the PySide6 plugin unless the app uses that toolkit.
The icon comes from `pyapp/icons/icon.ico`; entry script/Python version use normal developer
settings. Advanced metadata/compiler options can go in `extra_args`. Mode, console,
output/report paths and automatic execution flags are reserved by the tool.

## Commands and precedence

From the menu, *compile-app* asks which preset to build. From a terminal in `code/pyapp`:

```bat
"Open Developer Tools Menu.cmd" compilation-presets
"Open Developer Tools Menu.cmd" validate-syntax
"Open Developer Tools Menu.cmd" compile-app --dry-run
"Open Developer Tools Menu.cmd" compile-app --preset development
"Open Developer Tools Menu.cmd" compile-app --preset gui --keep
"Open Developer Tools Menu.cmd" compile-app no_terminal --preset onefile
"Open Developer Tools Menu.cmd" clean-compilation
```

CLI mode/variant choices override settings, which override preset defaults. Extra arguments are
additive: preset, structured options, then the settings' extra arguments.
`--dry-run` prints the effective command without preparing/installing an environment or compiling.

## Prerequisites and validation limits

The build automatically installs Nuitka, ordered-set and zstandard into a disposable package
directory under the marked compilation output folder. It uses the managed app Python, with
installed app package versions constraining dependency resolution. The app's `.venv`, package
declarations and lock file are not modified. Existing build packages are reused when all three
are already installed; those packages are never removed by the build tool.

Temporary packages are removed after success, installation/build failure or a handled Ctrl+C.
uv's download cache and shared compiler caches remain available for later builds. A forced
process kill can leave temporary files; *clean-compilation* deletes `code/pyapp/compiled`.
`--dry-run` and syntax validation do not install compiler packages. The first actual build
needs access to the package index unless downloads are already cached.

A supported C compiler is still needed; follow Nuitka's platform instructions. This temporary
package lifecycle does not install or uninstall the system C compiler.

*compile-app* builds for Windows. *compile-linux* builds inside WSL Linux from Windows; see the [Linux guide](LINUX.md).
Build on the target architecture. macOS builds are not provided.
A dry run or syntax check does not verify an executable, missing imports, runtime behavior or
packaged resources. Always test the distribution.

References: [Nuitka manual](https://nuitka.net/user-documentation/user-manual.html),
[standalone before onefile](https://nuitka.net/user-documentation/use-cases.html),
[resource paths/no-console diagnostics](https://nuitka.net/user-documentation/common-issue-solutions.html),
[compiler caching](https://nuitka.net/user-documentation/tips.html).

## Linux builds from Windows (WSL)

See the [Linux compilation guide](LINUX.md) for setup, settings and build commands.

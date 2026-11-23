# Standalone modules

Each file here works without the rest of this template. Copy it, together with any files of this
folder it names as needed, into another project and import or run it there.

- **Standard library only.** No packages to install and no imports from the launcher.
- **Files may use each other**, but only by relative import (`from . import com_tools`), and the
  docstring names every file needed next to it ("Needs com_tools.py next to it."). Copy them into
  one package folder (a folder you import from, e.g. `mytools/`) so the relative imports work.
- **A file that also runs as a script** (like `splash.py`) imports no other files from here, since
  relative imports do not work in a file started directly.
- **Python 3.8 or newer.**
- **Settings and paths are arguments or module constants**, never read from the template. The
  launcher passes them in from the module that uses the file (for example `scripts/desktop/splash.py`
  for `splash.py`).

`tests/src/test_files.py` (`StandaloneTests`) enforces these rules and checks that every file's
docstring contains "Standalone:". A file that needs a launcher import does not belong here.

The last column says which files must be copied along.

| File | What it does | Platform | Needs |
| --- | --- | --- | --- |
| `com_tools.py` | Minimal COM helpers with `ctypes`, no pywin32: GUID and property-store structures, error checks, COM setup per thread, and the AppUserModelID that groups a pinned shortcut with its window in the taskbar. | Windows | |
| `file_tools.py` | `FileLock` (one process at a time; Windows releases it after a crash), `atomic_json` (readers never see a half-written file), `remove_tree_inside` (deletes only inside a given folder, careful with junctions), `sanitize_filename`, path helpers. | Any; `FileLock` Windows | |
| `find_imports.py` | Which PyPI packages does a folder of code import? Scans with `ast` (no code runs), drops the standard library and local modules, marks imports in `try/except ImportError` as optional, and maps names to distributions from installed metadata, an optional mapping, or a guess. | Any | |
| `image_tools.py` | Builds multi-size `.ico` files from a PNG, with an optional overlay in a corner, and gives a PNG a stable ID from its decoded pixels. Uses Windows' own WPF through PowerShell, so no Pillow is needed. Small sizes are averaged in linear light and sharpened a little. | Windows | |
| `power.py` | `set_awake(prevent_sleep, keep_display_awake)` keeps Windows from going to sleep or turning off the display while something runs. The request belongs to the calling thread and ends with it. | Windows (does nothing elsewhere) | |
| `processes.py` | Process identities that survive PID reuse, a process and all its descendants, job objects (put this process into a named job, then end everything it started with one call), tree termination without a job, and Windows crash exit codes. | Windows | |
| `python_request.py` | Understands Python version requests that allow several versions (`"3"`, `">=3.12"`, `"3.12-3.14"`). It turns ranges into specifiers uv accepts and works out which version to record and whether a recorded version still matches. | Any | |
| `shortcut_files.py` | `create_shortcut(path, target, arguments, icon_path=..., working_dir=..., show_minimized=..., app_id=...)` writes a `.lnk`, replacing an existing one only with a complete new file. | Windows | `com_tools.py` |
| `splash.py` | A startup splash window, run as its own process: a dark card with the icon, the name in a color gradient, one message, a loading bar and a turning neon glow with smooth, truly transparent edges. | Windows for the glow; elsewhere the card alone | |
| `system_tray.py` | `MinimizeToTray`: a window goes to the notification area when minimized, with a notification, Restore/Stop menu and recovery after an Explorer restart. Works for windows of other processes too (e.g. a console). | Windows | `com_tools.py` |
| `taskbar.py` | `set_progress(hwnd, state)` (running animation, full green or red bar, clear) and `flash(hwnd)` for any window. | Windows | `com_tools.py` |

## Examples

```python
from image_tools import generate_ico_from_png

generate_ico_from_png("app.ico", "app.png")  # 256 down to 16 px
generate_ico_from_png("stop.ico", "app.png", "stop_overlay.png")  # overlay at the bottom right
```

```python
from power import set_awake

set_awake(prevent_sleep=True, keep_display_awake=False)
try:
    long_job()
finally:
    set_awake(False, False)  # from the same thread
```

```python
from file_tools import FileLock, atomic_json

with FileLock("state/.lock"):  # waits up to 120 s for another process
    atomic_json("state/status.json", {"step": 3})
```

```python
from find_imports import find_requirements, read_mapping

requirements, unreadable = find_requirements("src", site_packages=".venv/Lib/site-packages")
for requirement in requirements:
    print(requirement.distribution, requirement.imports, "optional" if requirement.optional else "")
```

```python
from python_request import range_specifier, request_matches

range_specifier("3.12-3.14")  # ">=3.12,<3.15"
request_matches(">=3.12", "3.13")  # True
```

The splash closes when its standard input closes, so the app decides when it goes away:

```python
import subprocess, sys

splash = subprocess.Popen(
    [sys.executable, "splash.py", "My App", "icon.png", "Loading ...", "0.5"],
    stdin=subprocess.PIPE,
)
...  # slow start-up work
splash.stdin.close()  # the splash stays at least 0.5 s, then closes
```

To try it on its own: `python splash.py "My App" icon.png "Loading ..." 5 preview` (closes after
5 seconds, on a click or on Escape). The icon must be a PNG or GIF; `""` shows a placeholder symbol.

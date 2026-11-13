"""Fallback start: run the app's main script without the launcher, for when the launcher is broken.

Started by code/pyapp/"Start without launcher.cmd", which picks the Python: the app's environment
(generated/.venv) if its Python still starts, otherwise the global default Python. This file is the
only one of DONT_CHANGE that runs: it imports nothing else from the launcher, and
developer_settings.py is only read, never executed, so a broken launcher or a mistake in the
settings cannot stop this start.

What the launcher would add is missing on purpose: setup, installing or syncing packages, the
log and crash log, tracebacks reports, single-instance rules, the STOP shortcut and window styling.
Standard library only, and Python 3.8 compatible, because the global Python may be an old one.

Not run by entrypoint.py like the other actions. Keep the file at this path: the .cmd outside
DONT_CHANGE names it (FALLBACK_START_PATH in backend_settings.PROTECTED_PATHS), so projects that
update by replacing DONT_CHANGE still find it.
"""

from __future__ import annotations

import ast
import contextlib
import io
import os
import platform
import re
import subprocess
import sys
import sysconfig
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LAUNCHER_DIR = Path(__file__).resolve().parents[1]  # pyapp/DONT_CHANGE
PYAPP_DIR = LAUNCHER_DIR.parent
SETTINGS_PATH = PYAPP_DIR / "developer_settings.py"
VENV_DIR = PYAPP_DIR / "generated" / ".venv"
ICON_PATH = PYAPP_DIR / "icons" / "icon.ico"
# Used when developer_settings.py lacks a setting or cannot be read at all.
DEFAULTS: Dict[str, object] = {
    "program_name": "App",
    "python_version": "",
    "main_script_path": "..\\main.py",
    "args_for_main_py": [],
    "environment_for_main_py": {},
    "packages": "",
    "requirements_path": "",
}
# Set by "Start without launcher.cmd": which Python it chose, and the state of the app's environment.
SOURCES = {
    "venv": "the app's environment",
    "py": "global default Python (py launcher)",
    "path": "global Python on PATH",
}
VENV_STATES = {
    "missing": "the app's environment does not exist yet (Setup creates it)",
    "broken": "the app's environment exists, but its Python does not start (moved or removed base Python?)",
}

USE_COLOR = sys.stdout.isatty()
# Windows Terminal turns these escape sequences into clickable links; the classic console would not.
USE_LINKS = USE_COLOR and bool(os.environ.get("WT_SESSION"))


def style(text: str, code: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if USE_COLOR else text


def link(path: Path) -> str:
    """The path as text, clickable where the terminal supports it."""
    text = str(path)
    return f"\x1b]8;;{path.as_uri()}\x1b\\{text}\x1b]8;;\x1b\\" if USE_LINKS and path.is_absolute() else text


def row(label: str, value: str, note: str = "") -> None:
    # Two spaces at least, so a long package name stays apart from its version.
    print(f"  {style(label.ljust(15), '90')}  {value}" + (f"  {style(note, '90')}" if note else ""))


def heading(text: str) -> None:
    print(f"\n {style(text, '1;36')}")


def warn(text: str) -> None:
    print(f"  {style('!', '1;33')} {text}")


def read_settings() -> Tuple[Dict[str, object], str]:
    """The plain values in developer_settings.py (the last assignment wins) and a problem, if any.

    Read with ast instead of importing: values that are expressions (e.g. f-strings) are skipped
    and fall back to DEFAULTS, and a file that does not even parse still allows a start.
    """
    values = dict(DEFAULTS)
    try:
        tree = ast.parse(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as error:
        return values, f"{type(error).__name__}: {error}"
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name):
            with contextlib.suppress(ValueError):
                values[target.id] = ast.literal_eval(value)
    return values, ""


def requirement_names(text: str) -> List[str]:
    """Distribution names from requirements text: comments, options and version limits are left out."""
    names: List[str] = []
    for line in text.replace("\\\n", " ").splitlines():
        requirement = line.split("#")[0].strip()  # the name always comes before a comment or URL fragment
        match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)
        if match:
            names.append(match.group(0))
    return names


def installed_version(name: str) -> Optional[str]:
    try:
        from importlib import metadata
    except ImportError:  # Python 3.7 or older
        return None
    for candidate in (name, re.sub(r"[-_.]+", "-", name).lower()):
        try:
            return metadata.version(candidate)
        except metadata.PackageNotFoundError:
            continue
    return None


def text_setting(settings: Dict[str, object], name: str) -> str:
    value = settings.get(name)
    return value if isinstance(value, str) else str(DEFAULTS[name])


def enable_color_sequences() -> None:
    """Let the classic Windows console interpret color sequences (Windows Terminal always does)."""
    if os.name != "nt":
        return
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_uint32()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING


def main() -> int:
    # Redirected output (a pipe, a file) uses the legacy code page on older Pythons, which has no ✓
    # or ✗; a real console is UTF-8 already.
    if isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if USE_COLOR:
        enable_color_sequences()
    settings, settings_problem = read_settings()
    program = text_setting(settings, "program_name")
    main_script = (PYAPP_DIR / text_setting(settings, "main_script_path")).resolve()
    arguments = [str(a) for a in settings["args_for_main_py"]] if isinstance(settings["args_for_main_py"], list) else []
    arguments += sys.argv[1:]  # what was passed to "Start without launcher.cmd"
    environment = settings["environment_for_main_py"]
    extra_env = {str(k): str(v) for k, v in environment.items()} if isinstance(environment, dict) else {}

    title = f" {program}  ·  started without the launcher "
    print()
    print(style(title, "1;30;43"))
    print(style(" " + "─" * (len(title) - 1), "33"))
    warn("The launcher (pyapp\\DONT_CHANGE) is bypassed. This start has no setup, no package")
    print("    installation or sync, no log or crash log, no single-instance check and no STOP shortcut.")
    print("    Use it to keep working or to find out what is broken; Setup repairs the launcher.")

    heading("App")
    row("Main script", link(main_script), "" if main_script.is_file() else style("not found", "1;31"))
    row("Working folder", link(main_script.parent))
    row("Arguments", " ".join(arguments) if arguments else "(none)")
    row("Environment", ", ".join(f"{k}={v}" for k, v in extra_env.items()) if extra_env else "(none extra)")
    row("Settings", link(SETTINGS_PATH), "read only, not run")
    if settings_problem:
        warn(f"developer_settings.py could not be read ({settings_problem}); using defaults.")
    row("Launcher", link(LAUNCHER_DIR), "not used (only this script from its actions folder)")

    heading("Python")
    source = os.environ.get("PYAPP_FALLBACK_SOURCE", "")
    venv_state = os.environ.get("PYAPP_FALLBACK_VENV", "")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    row("Executable", link(Path(sys.executable)))
    bits = platform.architecture()[0]
    row("Version", f"{platform.python_version()} ({platform.python_implementation()}, {bits})")
    row("Source", SOURCES.get(source, "started directly"), f"virtual environment {sys.prefix}" if in_venv else "")
    if in_venv:
        row("Base Python", link(Path(sys.base_prefix)))
    row("Packages folder", link(Path(sysconfig.get_paths()["purelib"])))
    if venv_state in VENV_STATES:
        warn(VENV_STATES[venv_state] + ":")
        print(f"    {link(VENV_DIR)}")
    requested = text_setting(settings, "python_version")
    wanted = re.match(r"\d+\.\d+", requested)
    running = f"{sys.version_info[0]}.{sys.version_info[1]}"
    if wanted and wanted.group(0) != running:
        warn(f'developer_settings.py asks for python_version = "{requested}"; this is {running}.')

    heading("Packages (from developer_settings.py)")
    names = requirement_names(text_setting(settings, "packages"))
    requirements_file = text_setting(settings, "requirements_path")
    if requirements_file:
        try:
            names += requirement_names((PYAPP_DIR / requirements_file).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            warn(f"requirements_path {requirements_file!r} could not be read: {error}")
    missing = []
    for name in names:
        version = installed_version(name)
        if version is None:
            missing.append(name)
        mark = style("✓", "1;32") if version else style("✗ missing", "1;31")
        row(name, f"{version or ''}  {mark}".strip())
    if not names:
        row("(none)", "")
    if missing:
        warn("Missing packages make the app fail on import. Install them into this Python with")
        print(f'    "{sys.executable}" -m pip install {" ".join(missing)}')
        print("    or repair the launcher (Setup) to get the app's own environment back.")

    if not main_script.is_file():
        print()
        print(style(f" ERROR  The main script does not exist: {main_script}", "1;31"))
        print("        Check main_script_path in developer_settings.py.")
        return 1

    env = {k: v for k, v in os.environ.items() if not k.startswith("PYAPP_")}
    env.update(extra_env)
    # The variables the launcher gives the app, as far as they make sense without it.
    env.update(PROGRAM_NAME=program, PROGRAM_HAS_TERMINAL="1", WDIR_IS_SCRIPT_DIR="1", LOG_PATH="")
    if ICON_PATH.is_file():
        env["ICON_PATH"] = str(ICON_PATH)
    command = [sys.executable, "-X", "utf8", str(main_script), *arguments]
    heading("Run")
    row("Command", subprocess.list2cmdline(command))
    # Flushed first: the app writes into the same window, and redirected output is buffered.
    print(style(" " + "─" * 70, "90"), flush=True)
    started = time.monotonic()
    # The app runs like `python main.py` from its folder; this window waits and reports how it ended.
    process = subprocess.Popen(command, cwd=str(main_script.parent), env=env)  # noqa: S603
    while True:
        try:
            code = process.wait()
            break
        except KeyboardInterrupt:  # Ctrl+C reaches the app too; wait for it to end
            continue
    seconds = time.monotonic() - started
    print(style(" " + "─" * 70, "90"))
    if code == 0:
        print(style(f" OK  {program} ended after {seconds:.1f} s.", "1;32"))
    else:
        print(style(f" EXIT CODE {code}  {program} ended after {seconds:.1f} s.", "1;31"))
    return code


if __name__ == "__main__":
    exit_code = 1
    try:
        exit_code = main()
    finally:
        # Double-clicked, the window would close before anything could be read.
        if sys.stdin.isatty():
            with contextlib.suppress(EOFError, KeyboardInterrupt):
                input(style("\n Press Enter to close this window.", "90"))
    sys.exit(exit_code)

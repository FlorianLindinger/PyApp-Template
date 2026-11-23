# Step 3 of a start (steps 1-2: B\W.bat and scripts\bootstrap\run.bat; see B\W.bat). This process runs in a
# small minimized window. It checks the settings, makes sure Python and the packages are ready, then
# starts scripts/runtime/bg_watchdog.py in the right kind of window, waits until it reports "started", and
# ends. From then on the watchdog owns the run: it starts code/main.py and reports how it ended.
"""Prepare the app environment and hand off one uniquely identified run to the watchdog."""

from __future__ import annotations

from types import ModuleType, SimpleNamespace
from typing import List, Optional, Union

fail_message = "Failed to start the program: {e}"

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from pyapp.DONT_CHANGE import pyapp_settings as paths
from pyapp.DONT_CHANGE.scripts.config import settings, terminal_color_code, validate
from pyapp.DONT_CHANGE.scripts.console_tools import print_warn
from pyapp.DONT_CHANGE.scripts.desktop.splash import startup_splash
from pyapp.DONT_CHANGE.scripts.diagnostics import note_ignored
from pyapp.DONT_CHANGE.scripts.env.venv import ensure_environment
from pyapp.DONT_CHANGE.scripts.instance_policy import decide
from pyapp.DONT_CHANGE.scripts.launcher_ui import (
    delete_finished_run_folders,
    set_terminal_appearance_once,
)
from pyapp.DONT_CHANGE.scripts.runtime_state import ProcessRegistry


def resolve_mode(s: Union[ModuleType, SimpleNamespace], requested: str) -> str:
    """Map the shortcut's request to conhost / wt / browser / no_terminal (with a Windows Terminal fallback)."""
    mode = requested
    if mode == "terminal":
        mode = "conhost" if s.use_classic_terminal else "wt"
    if mode not in {"conhost", "wt", "browser", "no_terminal"}:
        raise ValueError("Unknown launch mode: " + mode)
    if mode == "wt" and not shutil.which("wt.exe"):
        print_warn("Windows Terminal (wt.exe) is not installed; using the classic terminal instead.")
        mode = "conhost"
    return mode


def wt_command(title: str, tab_color: Optional[str], command: List[str], dedicated_window: bool = False) -> List[str]:
    """The wt.exe command line that runs `command` in a new Windows Terminal tab.

    wt.exe splits its own command line at ";" into several subcommands, so a ";" in the title or
    in a path (e.g. a project folder "R;D") is escaped as "\\;", which wt.exe passes on as ";".
    """
    arguments = [title, *(["--tabColor", tab_color] if tab_color else []), *command]
    # Window-wide styles must never affect another app's tabs. Application titles let the
    # watchdog identify its window by a temporary random title before app startup.
    window = ["--window", "new", "new-tab", "--useApplicationTitle"] if dedicated_window else []
    return ["wt.exe", *window, "--title", *(argument.replace(";", "\\;") for argument in arguments)]


def _python_version_note() -> str:
    """The environment's Python version from its pyvenv.cfg, as " (3.14.2)", or "" if unknown."""
    try:
        for line in (Path(paths.VENV_DIR) / "pyvenv.cfg").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() in ("version", "version_info"):
                return f" ({value.strip()})"
    except OSError:
        pass
    return ""


def browser_command(s: Union[ModuleType, SimpleNamespace], run_dir: Path, command: List[str]) -> List[str]:
    """The command line that runs `command` in the browser terminal, after writing its settings.

    The browser_terminal package fills in everything not set here (see its host.complete_config).
    """
    from pyapp.DONT_CHANGE.browser_terminal.ui import colors_from_code
    from pyapp.DONT_CHANGE.scripts import browser_links
    from pyapp.DONT_CHANGE.scripts.desktop.shortcuts import project_app_id, read_start_link, shortcut_targets
    from pyapp.DONT_CHANGE.scripts.launcher_ui import get_log_folder_path

    colors = colors_from_code(terminal_color_code(s.terminal_bg_color, s.terminal_text_color))
    # The same address on every start (and the one Setup shows), so it can be bookmarked.
    app_id = project_app_id(s.program_name)
    host_name, port, key = browser_links.address(s, app_id)
    start_link = read_start_link()
    if start_link != browser_links.scheme(app_id):
        start_link = ""  # recorded for an earlier program name; Setup has not run since
    # The page's open buttons match the shortcuts: each only if its shortcut is wanted.
    targets = shortcut_targets(s)
    log_folder = get_log_folder_path(s.log_path, s.log_path_is_relative_to_start_folder_if_relative) or ""
    crash_folder = get_log_folder_path(s.crash_log_path, s.crash_log_path_is_relative_to_start_folder_if_relative) or ""
    info = [
        ["Program", targets["open_code"]],
        ["Python", paths.VENV_PYTHON_EXE + _python_version_note()],
        ["Environment", paths.VENV_DIR],
        ["Project", str(Path(paths.BACKEND_DIR).parents[1])],
        ["Working folder", "starting..."],
        ["Settings file", targets["settings"] or "off"],
        ["Developer settings", paths.DEV_SETTINGS_PATH],
        ["Logs", log_folder or "off"],
        ["Crash logs", crash_folder or "off"],
        ["Current log file", "starting..."],
        ["Launcher", "PyApp-Template " + paths.LAUNCHER_VERSION],
        ["Browser terminal", str(Path(paths.DONT_CHANGE_DIR) / "browser_terminal")],
        ["Browser terminal settings", str(Path(paths.DONT_CHANGE_DIR) / "browser_terminal" / "settings.py")],
    ]
    config = {
        "start_maximized": getattr(s, "start_maximized", False),
        "confirm_on_close": s.confirm_on_close,
        "wrap_output": s.wrap_terminal_output,
        "prefix_controls": True,
        "title": s.program_name,
        "info": info,
        "code_file": targets["open_code"] if s.open_code_shortcut_name else "",
        "settings_file": targets["settings"] if s.open_settings_shortcut_name else "",
        "log_path": log_folder if s.open_log_folder_shortcut_name else "",
        "crash_log_path": crash_folder if s.open_crash_log_folder_shortcut_name else "",
        "host_name": host_name,
        "port": port,
        "key": key,
        # Offered by the page's bookmark hint, if Setup registered it.
        "start_link": f"{start_link}://start" if start_link else "",
        "icon": paths.ICON_PATH,
        "theme": {**colors, "cursor": colors["foreground"]},
        "state_dir": str(run_dir),
        "ui_file": str(run_dir / paths.BROWSER_UI_FILE_NAME),
        "window_file": str(run_dir / paths.BROWSER_WINDOW_FILE_NAME),
        "ui_env_var": paths.BROWSER_UI_ENV_VAR,
        # The browser may outlive this run (when it was not running yet).
        "hidden_env_prefixes": ["PYAPP_"],
    }
    config_path = run_dir / paths.BROWSER_CONFIG_FILE_NAME
    config_path.write_text(json.dumps(config), encoding="utf-8")
    python = [sys.executable, "-I", "-S", "-X", "utf8"]
    return [*python, paths.BROWSER_TERMINAL_PATH, "--config", str(config_path), "--", *command]


def main() -> int:
    """Apply the instance policy, prepare the environment, start the watchdog and wait for it."""
    # --- 1. What to start and how. sys.argv is the list of command-line arguments: [script, app ID, ...].
    # The app ID is the taskbar identity Setup wrote into the shortcut. os.environ holds the
    # environment variables; PYAPP_LAUNCH_MODE was set by the B\*.bat file (terminal, no_terminal, ...).
    app_id = sys.argv[1] if len(sys.argv) > 1 else ""
    requested = os.environ.pop("PYAPP_LAUNCH_MODE", "") or (sys.argv[2] if len(sys.argv) > 2 else "terminal")
    # Load developer_settings.py (s.program_name, s.instance_policy, ...) and check every value.
    s = settings()
    validate(s)
    mode = resolve_mode(s, requested)
    from pyapp.DONT_CHANGE.scripts.desktop.terminal_window import needs_window, validate_close_mode

    validate_close_mode(s, mode)
    if mode == "wt" and (
        s.hide_minimize_button or s.hide_maximize_button or not s.allow_minimize or not s.allow_maximize
    ):
        print_warn(
            "Windows Terminal owns its caption actions; hide/allow minimize/maximize settings apply only to conhost."
        )
    # This (minimized) window shows progress while the environment is prepared: give it the
    # app's title, icon and taskbar group.
    set_terminal_appearance_once(app_id)

    # --- 2. Is the app running already? Each running copy has a small record file in
    # DONT_CHANGE\tmp\running. instance_policy decides: start another, focus the old one, refuse,
    # replace it, or ask.
    # Quick check before any environment work; the watchdog repeats it under the registry lock.
    registry = ProcessRegistry(paths.PROCESS_REGISTRY_DIR)
    records, _ = registry.records()
    decision = decide(s.instance_policy, records, s.program_name)
    if decision == "cancel":
        # pyapp_api.on_new_start: a running copy that listens gets this start's arguments instead.
        from pyapp.DONT_CHANGE.scripts.app_api_support import forward_start

        try:
            arguments = sys.argv[2:] if os.environ.get("PYAPP_BATCH_ARGUMENTS", "") == "1" else []
            forward_start(arguments, os.environ.get("PYAPP_START_DIR", str(Path.cwd())))
        except OSError:
            note_ignored("forward a start to the running instance")
        return 0
    if decision == "replace":
        _, _, errors = registry.stop(s.stop_timeout_seconds, report=print)
        if errors:
            raise RuntimeError("Could not stop the running instance(s): " + "; ".join(errors))

    with startup_splash(s, mode):
        # --- 3. Housekeeping, then the environment: ensure_environment() creates code/pyapp/generated/.venv
        # and installs the packages from uv.lock when something changed; usually it only checks and returns.
        delete_finished_run_folders()
        from pyapp.DONT_CHANGE.scripts.hidden_caches import hide_cache_folders

        hide_cache_folders()  # e.g. code\__pycache__ from the previous run
        app = ensure_environment(interactive=True)

        # --- 4. A folder for this run (DONT_CHANGE\tmp\runs\<random name>): the processes of this run
        # exchange files there, such as the startup status and the crash report.
        # Keep run paths short; mkdir reserves the name even with concurrent launches.
        while True:
            run_dir = Path(paths.RUNS_DIR) / uuid.uuid4().hex[:12]
            try:
                run_dir.mkdir(parents=True)
            except FileExistsError:
                continue
            break
        # Information for the watchdog travels as environment variables, which a started process inherits.
        env = os.environ.copy()
        env["PYAPP_RUN_DIR"] = str(run_dir)
        env["PYAPP_START_DIR"] = env.get("PYAPP_START_DIR", str(Path.cwd()))
        env["PYAPP_APP_PYTHON"] = json.dumps({"exe": app.exe, "flags": list(app.flags)})
        # Shortcut argument 1 is the app ID. Batch launchers use the same protocol and append
        # application arguments; JSON preserves empty strings and quoted spaces across hosts.
        extra = sys.argv[2:] if os.environ.pop("PYAPP_BATCH_ARGUMENTS", "") == "1" else []
        env["PYAPP_EXTRA_ARGS"] = json.dumps(extra)
        # --- 5. The command that starts the watchdog. -I -S: ignore installed packages (the launcher uses
        # only Python's standard library); -X faulthandler: print a Python traceback even on a hard crash.
        args = [
            sys.executable,
            "-I",
            "-S",
            "-X",
            "utf8",
            "-X",
            "faulthandler",
            paths.WATCHDOG_PATH,
            app_id or paths.EMPTY_ARG_INDICATOR,
            mode,
        ]
        # Window options for the new process; 7 means "minimized, without taking the focus".
        startup = subprocess.STARTUPINFO()
        if s.start_minimized and not s.start_maximized:
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 7
        # Wrap the command for the chosen window: Windows Terminal (wt), the classic console (conhost),
        # or the browser terminal's host. Without a terminal the command runs as it is, hidden.
        if mode == "wt":
            args = wt_command(s.program_name, s.tab_bar_color, args, dedicated_window=needs_window(s))
        elif mode == "conhost":
            args = [paths.CONHOST_EXE, *args]
        elif mode == "browser":
            args = browser_command(s, run_dir, args)
            # Windows lets the process started by the click bring windows to the front; the browser
            # opens later from the hidden host, so this process passes that right on (ASFW_ANY).
            try:
                import ctypes

                ctypes.windll.user32.AllowSetForegroundWindow(-1)
            except Exception:
                note_ignored("AllowSetForegroundWindow for the browser terminal")
        # The browser terminal's host has no window of its own, like the watchdog without a terminal.
        hidden = mode in ("no_terminal", "browser")
        # --- 6. Start it, then wait until the watchdog writes startup.json ("started" or an error).
        # subprocess.Popen starts a program and returns at once, without waiting for it to end.
        with Path(run_dir / "bootstrap.log").open("w", encoding="utf-8") as diagnostics:
            # The configured launcher/interpreter is intentional; program arguments remain separate.
            child = subprocess.Popen(  # noqa: S603
                args,
                env=env,
                startupinfo=startup,
                creationflags=subprocess.CREATE_NO_WINDOW if hidden else subprocess.CREATE_NEW_CONSOLE,
                stdout=diagnostics if hidden else None,
                stderr=diagnostics if hidden else None,
            )
            deadline = time.monotonic() + paths.STARTUP_ACKNOWLEDGEMENT_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                # Before reading the status: a watchdog that cancels the launch writes "cancelled" and
                # exits at once, which must not look like an exit before startup.
                # wt.exe may exit after handing its command to an existing terminal window.
                exited = mode != "wt" and child.poll() is not None
                try:
                    status = json.loads((run_dir / "startup.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):  # not written yet, or being replaced right now
                    status = None
                if status:
                    if status["status"] in {"started", "cancelled"}:
                        return 0
                    raise RuntimeError(status.get("message", "Watchdog startup failed"))
                if exited:
                    raise RuntimeError("The watchdog exited before startup. See " + str(run_dir / "bootstrap.log"))
                time.sleep(0.05)
        raise TimeoutError("No startup acknowledgement. See " + str(run_dir))

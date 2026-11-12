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

from pyapp.DONT_CHANGE import backend_settings as paths
from pyapp.DONT_CHANGE.scripts.config import settings, terminal_color_code, validate
from pyapp.DONT_CHANGE.scripts.console_tools import print_info, print_warn
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


def _hint_outdated_shortcuts(s: Union[ModuleType, SimpleNamespace]) -> None:
    """The "open" shortcuts store their target; tell the user when the settings changed it."""
    try:
        from pyapp.DONT_CHANGE.scripts.shortcuts import outdated_shortcut_targets

        outdated = outdated_shortcut_targets(s)
        if outdated:
            print_info(
                "These shortcuts still open the previous location: "
                + ", ".join(outdated)
                + ". Run 'Setup - run first and after moving folder.cmd' to update them."
            )
    except Exception:
        note_ignored("outdated shortcut check")


def wt_command(title: str, tab_color: Optional[str], command: List[str]) -> List[str]:
    """The wt.exe command line that runs `command` in a new Windows Terminal tab.

    wt.exe splits its own command line at ";" into several subcommands, so a ";" in the title or
    in a path (e.g. a project folder "R;D") is escaped as "\\;", which wt.exe passes on as ";".
    """
    arguments = [title, *(["--tabColor", tab_color] if tab_color else []), *command]
    return ["wt.exe", "--title", *(argument.replace(";", "\\;") for argument in arguments)]


def browser_command(s: Union[ModuleType, SimpleNamespace], run_dir: Path, command: List[str]) -> List[str]:
    """The command line that runs `command` in the browser terminal, after writing its settings.

    The browser_terminal package fills in everything not set here (see its host.complete_config).
    """
    from pyapp.DONT_CHANGE.browser_terminal.ui import colors_from_code
    from pyapp.DONT_CHANGE.scripts import browser_links
    from pyapp.DONT_CHANGE.scripts.shortcuts import project_app_id, read_start_link

    colors = colors_from_code(terminal_color_code(s.terminal_bg_color, s.terminal_text_color))
    # The same address on every start (and the one Setup shows), so it can be bookmarked.
    app_id = project_app_id(s.program_name)
    host_name, port, key = browser_links.address(s, app_id)
    start_link = read_start_link()
    if start_link != browser_links.scheme(app_id):
        start_link = ""  # recorded for an earlier program name; Setup has not run since
    config = {
        "title": s.program_name,
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
    app_id = sys.argv[1] if len(sys.argv) > 1 else ""
    requested = os.environ.pop("PYAPP_LAUNCH_MODE", "") or (sys.argv[2] if len(sys.argv) > 2 else "terminal")
    s = settings()
    validate(s)
    mode = resolve_mode(s, requested)
    # This (minimized) window shows progress while the environment is prepared: give it the
    # app's title, icon and taskbar group.
    set_terminal_appearance_once(app_id)

    # Quick check before any environment work; the watchdog repeats it under the registry lock.
    registry = ProcessRegistry(paths.PROCESS_REGISTRY_DIR)
    records, _ = registry.records()
    decision = decide(s.instance_policy, records, s.program_name)
    if decision == "cancel":
        return 0
    if decision == "replace":
        _, _, errors = registry.stop(s.stop_timeout_seconds, report=print)
        if errors:
            raise RuntimeError("Could not stop the running instance(s): " + "; ".join(errors))

    delete_finished_run_folders()
    _hint_outdated_shortcuts(s)
    app = ensure_environment(interactive=True)

    # Keep run paths short; mkdir reserves the name even with concurrent launches.
    while True:
        run_dir = Path(paths.RUNS_DIR) / uuid.uuid4().hex[:12]
        try:
            run_dir.mkdir(parents=True)
        except FileExistsError:
            continue
        break
    env = os.environ.copy()
    env["PYAPP_RUN_DIR"] = str(run_dir)
    env["PYAPP_START_DIR"] = env.get("PYAPP_START_DIR", str(Path.cwd()))
    env["PYAPP_APP_PYTHON"] = json.dumps({"exe": app.exe, "flags": list(app.flags)})
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
    startup = subprocess.STARTUPINFO()
    if s.start_minimized:
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 7
    if mode == "wt":
        args = wt_command(s.program_name, s.tab_bar_color, args)
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

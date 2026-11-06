"""Prepare the app environment and hand off one uniquely identified run to the watchdog."""

from __future__ import annotations

fail_message = "[Error] Failed to start the program: {e}"

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from backend.DONT_CHANGE import backend_settings as paths
from backend.DONT_CHANGE.scripts.config import settings, validate
from backend.DONT_CHANGE.scripts.diagnostics import note_ignored
from backend.DONT_CHANGE.scripts.env.venv import ensure_environment
from backend.DONT_CHANGE.scripts.instance_policy import decide
from backend.DONT_CHANGE.scripts.launcher_ui import (
    prune_logs,
    set_hidden_in_explorer,
    set_terminal_appearance_once,
)
from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry


def resolve_mode(s, requested: str) -> str:
    """Map the shortcut's request to conhost / wt / no_terminal (with a Windows Terminal fallback)."""
    mode = requested
    if mode == "terminal":
        mode = "conhost" if s.use_classic_terminal else "wt"
    if mode not in {"conhost", "wt", "no_terminal"}:
        raise ValueError("Unknown launch mode: " + mode)
    if mode == "wt" and not shutil.which("wt.exe"):
        print("[Warning] Windows Terminal (wt.exe) is not installed; using the classic terminal instead.")
        mode = "conhost"
    return mode


def _hint_outdated_shortcuts(s) -> None:
    """The "open" shortcuts store their target; tell the user when the settings changed it."""
    try:
        from backend.DONT_CHANGE.scripts.shortcuts import outdated_shortcut_targets

        outdated = outdated_shortcut_targets(s)
        if outdated:
            print(
                "[Info] These shortcuts still open the previous location: "
                + ", ".join(outdated)
                + ". Run 'Setup - run first and after moving folder.cmd' to update them."
            )
    except Exception:
        note_ignored("outdated shortcut check")


def main():
    """Apply the instance policy, prepare the environment, start the watchdog and wait for it."""
    app_id = sys.argv[1] if len(sys.argv) > 1 else ""
    requested = os.environ.pop("PYAPP_LAUNCH_MODE", "") or (sys.argv[2] if len(sys.argv) > 2 else "terminal")
    s = settings()
    validate(s)
    mode = resolve_mode(s, requested)
    # This (minimized) window shows progress while the environment is prepared: give it the
    # app's title, icon and taskbar group, and keep tool folders out of sight in Explorer.
    set_terminal_appearance_once(app_id)
    set_hidden_in_explorer()

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

    prune_logs(s)
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
    env["PYAPP_START_DIR"] = env.get("PYAPP_START_DIR", os.getcwd())
    env["PYAPP_APP_PYTHON"] = json.dumps({"exe": app.exe, "flags": list(app.flags), "kind": app.kind})
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
        args = [
            "wt.exe",
            "--title",
            s.program_name,
            *(["--tabColor", s.tab_bar_color] if s.tab_bar_color else []),
            *args,
        ]
    elif mode == "conhost":
        args = ["conhost.exe", *args]
    with open(run_dir / "bootstrap.log", "w", encoding="utf-8") as diagnostics:
        child = subprocess.Popen(
            args,
            env=env,
            startupinfo=startup,
            creationflags=subprocess.CREATE_NO_WINDOW if mode == "no_terminal" else subprocess.CREATE_NEW_CONSOLE,
            stdout=diagnostics if mode == "no_terminal" else None,
            stderr=diagnostics if mode == "no_terminal" else None,
        )
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                status = json.loads((run_dir / "startup.json").read_text(encoding="utf-8"))
            except (FileNotFoundError, ValueError):
                status = None
            if status:
                if status["status"] in {"started", "cancelled"}:
                    return 0
                raise RuntimeError(status.get("message", "Watchdog startup failed"))
            # wt.exe may exit after handing its command to an existing terminal window.
            if mode != "wt" and child.poll() is not None:
                raise RuntimeError("The watchdog exited before startup. See " + str(run_dir / "bootstrap.log"))
            time.sleep(0.05)
    raise TimeoutError("No startup acknowledgement. See " + str(run_dir))

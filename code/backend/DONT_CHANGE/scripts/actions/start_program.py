# ruff: noqa: E402
# The early __main__ handoff lets the shared runner report import failures once.

"""Prepare the app environment and hand off one uniquely identified run to the watchdog."""

from __future__ import annotations

if __name__ == "__main__":
    import sys
    from pathlib import Path

    code_dir = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "backend" / "DONT_CHANGE").is_dir()
    )
    sys.path.insert(0, str(code_dir))
    from backend.DONT_CHANGE.scripts.entrypoint import run_file

    raise SystemExit(run_file(__file__))

fail_message = "[Error] Failed to start the program: {e}"
close_terminal_on_finish = True

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from backend.DONT_CHANGE.scripts.config import settings, validate
from backend.DONT_CHANGE.scripts.instance_policy import decide
from backend.DONT_CHANGE.scripts.launcher_ui import prune_logs
from backend.DONT_CHANGE.scripts.runtime_state import ProcessRegistry
from backend.DONT_CHANGE.scripts.uv_env import ensure_environment
from backend.DONT_CHANGE import backend_settings as paths


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


def main():
    """Apply the instance policy, prepare the environment, start the watchdog and wait for it."""
    app_id = sys.argv[1] if len(sys.argv) > 1 else ""
    requested = os.environ.pop("PYAPP_LAUNCH_MODE", "") or (sys.argv[2] if len(sys.argv) > 2 else "terminal")
    s = settings()
    validate(s)
    mode = resolve_mode(s, requested)

    # Quick check before any environment work; the watchdog repeats it under the registry lock.
    registry = ProcessRegistry(paths.PROCESS_ID_FILE_PATH)
    records, _ = registry.records()
    decision = decide(s.instance_policy, records, s.program_name)
    if decision == "cancel":
        return 0
    if decision == "replace":
        _, _, errors = registry.stop()
        if errors:
            raise RuntimeError("Could not stop the running instance(s): " + "; ".join(errors))

    prune_logs(s)
    app = ensure_environment(interactive=True)

    run_dir = Path(paths.RUNS_DIR) / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
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
        paths.BACKGROUND_WATCHDOG_PATH,
        app_id or paths.EMPTY_ARG_INDICATOR,
        mode,
    ]
    startup = subprocess.STARTUPINFO()
    if s.start_minimized:
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 7
    if mode == "wt":
        args = ["wt.exe", "--title", s.program_name, *(["--tabColor", s.tab_bar_color] if s.tab_bar_color else []), *args]
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

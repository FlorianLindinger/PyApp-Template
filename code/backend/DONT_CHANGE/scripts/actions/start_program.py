"""Prepare a managed environment and hand off one uniquely identified run."""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from backend import developer_settings as settings
from backend.DONT_CHANGE.scripts.frontend_environment import ensure_frontend_packages
from backend.DONT_CHANGE.scripts.launcher_ui import print_traceback
from backend.DONT_CHANGE.scripts.runtime_state import FileLock
from backend.DONT_CHANGE.settings import backend_settings as paths


def main():
    app_id = sys.argv[1] if len(sys.argv) > 1 else ""
    batch_mode = os.environ.pop("PYAPP_LAUNCH_MODE", "")
    mode = batch_mode or (sys.argv[2] if len(sys.argv) > 2 else "terminal")
    if mode == "terminal":
        mode = "conhost" if settings.use_classic_terminal else "wt"
    if mode not in {"conhost", "wt", "no_terminal"}:
        raise ValueError("Unknown launch mode: " + mode)
    if not settings.use_global_python:
        with FileLock(Path(paths.TEMPORARY_DIR) / "environment.lock", timeout=600):
            ensure_frontend_packages(app_id)
    run_dir = Path(paths.TEMPORARY_DIR) / "runs" / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    env = os.environ.copy()
    env["PYAPP_RUN_DIR"] = str(run_dir)
    env.pop("PYAPP_MAIN_ARGS", None)
    env["PYAPP_START_DIR"] = env.get("PYAPP_START_DIR", os.getcwd())
    args = [
        paths.BACKEND_PYTHON_EXE,
        "-X",
        "faulthandler",
        paths.BACKGROUND_WATCHDOG_PATH,
        app_id or paths.EMPTY_ARG_INDICATOR,
        mode,
    ]
    startup = subprocess.STARTUPINFO()
    if settings.start_minimized:
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 7
    if mode == "wt":
        args = [
            "wt.exe",
            "--title",
            settings.program_name,
            *(["--tabColor", settings.tab_bar_color] if settings.tab_bar_color else []),
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
                if status["status"] in {"started", "cancelled"}:
                    return 0
                raise RuntimeError(status.get("message", "Watchdog startup failed"))
            except FileNotFoundError:
                pass
            # wt.exe may exit after handing its command to an existing terminal server.
            if mode != "wt" and child.poll() is not None:
                raise RuntimeError("Watchdog exited before startup. See " + str(run_dir / "bootstrap.log"))
            time.sleep(0.05)
    raise TimeoutError("No startup acknowledgement. See " + str(run_dir))


if __name__ == "__main__":
    try:
        with FileLock(Path(paths.TEMPORARY_DIR) / "environment.lock", timeout=600):
            raise SystemExit(main())
    except Exception as error:
        print_traceback(str(error))
        if sys.stdin is not None and sys.stdin.isatty():
            input("Press Enter to exit")
        raise SystemExit(1)
